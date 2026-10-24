"""Cross-platform subprocess wrapper for the isolated candidate harness."""

from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


HARNESS_PATH = Path(__file__).with_name("harness.py")
MAX_STDOUT_BYTES = 1024 * 1024
_READ_SIZE = 16 * 1024
_WINDOWS_MEMORY_LIMIT = 256 * 1024 * 1024


def _minimal_environment() -> dict[str, str]:
    if os.name != "nt":
        return {}
    system_root = os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR")
    if not system_root:
        return {}
    system_root = os.path.abspath(system_root)
    system32 = os.path.join(system_root, "System32")
    # Python needs SYSTEMROOT to load its runtime DLLs. COMSPEC is included so
    # a candidate's os.system('echo ...') can be silenced by the harness.
    return {
        "SYSTEMROOT": system_root,
        "WINDIR": system_root,
        "COMSPEC": os.path.join(system32, "cmd.exe"),
    }


def _attach_windows_job(process: subprocess.Popen[bytes]) -> Any | None:
    """Apply a process memory cap and kill descendants when the job closes."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = ExtendedLimitInformation()
        # JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        info.BasicLimitInformation.LimitFlags = 0x100 | 0x2000
        info.ProcessMemoryLimit = _WINDOWS_MEMORY_LIMIT
        ok = kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ok or not kernel32.AssignProcessToJobObject(
            job, wintypes.HANDLE(process._handle)  # type: ignore[attr-defined]
        ):
            kernel32.CloseHandle(job)
            return None
        return job
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _close_windows_job(job: Any | None) -> None:
    if job is None or os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(wintypes.HANDLE(job))
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        taskkill = shutil.which("taskkill")
        if taskkill is None:
            system_root = os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR", "")
            candidate = os.path.join(system_root, "System32", "taskkill.exe")
            taskkill = candidate if os.path.isfile(candidate) else None
        if taskkill is not None:
            try:
                subprocess.run(
                    [taskkill, "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass


def _stdout_reader(
    fd: int,
    events: queue.Queue[tuple[str, bytes | None]],
    max_lines: int,
) -> None:
    buffer = bytearray()
    total_bytes = 0
    line_count = 0
    try:
        while True:
            chunk = os.read(fd, _READ_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_STDOUT_BYTES:
                events.put(("output_too_large", None))
                return
            buffer.extend(chunk)
            while True:
                newline = buffer.find(b"\n")
                if newline < 0:
                    break
                line = bytes(buffer[:newline])
                del buffer[: newline + 1]
                line_count += 1
                if line_count > max_lines:
                    events.put(("output_too_large", None))
                    return
                events.put(("line", line))
        if buffer:
            line_count += 1
            if line_count > max_lines:
                events.put(("output_too_large", None))
                return
            events.put(("line", bytes(buffer)))
        events.put(("eof", None))
    except OSError:
        events.put(("eof", None))


def _stderr_drainer(fd: int) -> None:
    try:
        while os.read(fd, _READ_SIZE):
            pass
    except OSError:
        pass


def _gen_parameters(inputs: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Read gen settings from its sole config dict or per-request dicts.

    The public function signature has no n/size/seed parameters, so gen callers
    pass them in inputs as ``[{"n": 20, "size": 8, "seed": 123}]``. When
    several dictionaries are passed, their count is n and the first dictionary
    supplies size and seed. Empty inputs default to one empty-size generation.
    """
    if not inputs:
        return 1, 0, 0
    config = inputs[0]
    n = int(config.get("n", 1 if len(inputs) == 1 else len(inputs)))
    size = int(config.get("size", 0))
    seed = int(config.get("seed", 0))
    return max(0, n), size, seed


def _decode_line(
    mode: str,
    raw_line: bytes,
    expected_index: int,
) -> dict[str, Any]:
    try:
        decoded = json.loads(raw_line)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"err": "Invalid harness output"}
    if mode == "gen":
        if isinstance(decoded, dict) and isinstance(decoded.get("err"), str):
            return {"err": decoded["err"]}
        if isinstance(decoded, list) and all(isinstance(item, dict) for item in decoded):
            return {"ok": decoded}
        return {"err": "Invalid generator output"}
    if not isinstance(decoded, dict) or decoded.get("i") != expected_index:
        return {"err": "Out-of-order or invalid harness result"}
    if isinstance(decoded.get("err"), str):
        return {"err": decoded["err"]}
    if "ok" in decoded:
        return {"ok": decoded["ok"]}
    return {"err": "Invalid harness result"}


def run_in_sandbox(
    mode: str,
    code: str,
    method: str,
    inputs: list[dict[str, Any]],
    per_case_timeout: float,
    wall_timeout: float,
) -> list[dict[str, Any]]:
    """Run candidate code and return one outcome dictionary per input.

    Solve outcomes are ``{"ok": value}``, ``{"err": message}``,
    ``{"timeout": True}``, ``{"skipped": True}``, or
    ``{"output_too_large": True}``. Gen mode returns one outcome whose ok
    value is the generated list. For gen mode, pass n/size/seed in the first
    input dictionary as described in :func:`_gen_parameters`.
    """
    if mode not in {"gen", "solve"}:
        raise ValueError("mode must be 'gen' or 'solve'")
    if not isinstance(inputs, list) or any(not isinstance(item, dict) for item in inputs):
        raise TypeError("inputs must be a list of dictionaries")
    if per_case_timeout <= 0 or wall_timeout <= 0:
        raise ValueError("timeouts must be positive")

    if mode == "solve":
        gen_n, size, seed = len(inputs), 0, 0
        result_count = len(inputs)
        protocol_line_limit = result_count
    else:
        gen_n, size, seed = _gen_parameters(inputs)
        result_count = 1
        protocol_line_limit = 1

    request = {
        "mode": mode,
        "code": code,
        "method": method,
        "inputs": inputs,
        "per_case_timeout": float(per_case_timeout),
        "n": gen_n,
        "size": size,
        "seed": seed,
    }
    try:
        request_bytes = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        return [{"err": f"Invalid request: {error}"} for _ in range(result_count)]

    results: list[dict[str, Any] | None] = [None] * result_count
    events: queue.Queue[tuple[str, bytes | None]] = queue.Queue()
    process: subprocess.Popen[bytes] | None = None
    job = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    next_index = 0
    stopped_for_timeout = False
    stopped_for_output = False
    started = time.monotonic()
    wall_deadline = started + wall_timeout

    def mark_unfinished(outcome: dict[str, Any]) -> None:
        nonlocal next_index
        if next_index < result_count:
            results[next_index] = outcome
            next_index += 1
        while next_index < result_count:
            results[next_index] = {"skipped": True}
            next_index += 1

    with tempfile.TemporaryDirectory(prefix="verifier-sandbox-") as workdir:
        try:
            kwargs: dict[str, Any] = {
                "stdin": subprocess.PIPE,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "cwd": workdir,
                "env": _minimal_environment(),
                "bufsize": 0,
            }
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True
            process = subprocess.Popen(
                [sys.executable, "-I", str(HARNESS_PATH)], **kwargs
            )
            job = _attach_windows_job(process)
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            stdout_thread = threading.Thread(
                target=_stdout_reader,
                args=(process.stdout.fileno(), events, protocol_line_limit),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_stderr_drainer,
                args=(process.stderr.fileno(),),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            try:
                view = memoryview(request_bytes)
                while view:
                    written = process.stdin.write(view)
                    if not written:
                        break
                    view = view[written:]
                process.stdin.close()
            except (BrokenPipeError, OSError):
                try:
                    process.stdin.close()
                except OSError:
                    pass

            per_result_wait = (
                per_case_timeout
                if mode == "solve"
                else per_case_timeout * max(gen_n, 1)
            )
            while next_index < result_count:
                remaining_wall = wall_deadline - time.monotonic()
                remaining_case = per_result_wait
                wait_for = min(remaining_wall, remaining_case)
                if wait_for <= 0:
                    stopped_for_timeout = True
                    _kill_process_tree(process)
                    mark_unfinished({"timeout": True})
                    break
                try:
                    kind, payload = events.get(timeout=wait_for)
                except queue.Empty:
                    # Resolve the edge where a line arrived as the deadline
                    # expired but its reader thread had not queued it yet.
                    try:
                        kind, payload = events.get_nowait()
                    except queue.Empty:
                        stopped_for_timeout = True
                        _kill_process_tree(process)
                        mark_unfinished({"timeout": True})
                        break

                if kind == "output_too_large":
                    stopped_for_output = True
                    _kill_process_tree(process)
                    mark_unfinished({"output_too_large": True})
                    break
                if kind == "eof":
                    stopped_for_timeout = True
                    mark_unfinished({"timeout": True})
                    break
                assert payload is not None
                results[next_index] = _decode_line(mode, payload, next_index)
                next_index += 1

            # Reap a normal child and catch oversized trailing stdout. A child
            # that finishes every case but leaves a thread running is still
            # killed at the wall deadline.
            if not stopped_for_timeout and not stopped_for_output:
                remaining_wall = max(0.0, wall_deadline - time.monotonic())
                try:
                    process.wait(timeout=remaining_wall)
                except subprocess.TimeoutExpired:
                    stopped_for_timeout = True
                    _kill_process_tree(process)
                if stdout_thread is not None:
                    stdout_thread.join(timeout=1.0)
                while True:
                    try:
                        kind, _payload = events.get_nowait()
                    except queue.Empty:
                        break
                    if kind == "output_too_large":
                        stopped_for_output = True
                        if next_index < result_count:
                            mark_unfinished({"output_too_large": True})
                        elif results:
                            results[-1] = {"output_too_large": True}
                        _kill_process_tree(process)
                        break
        except OSError as error:
            if next_index < result_count:
                mark_unfinished({"err": f"SandboxError: {error}"})
        finally:
            if process is not None:
                if process.poll() is None:
                    _kill_process_tree(process)
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        try:
                            process.kill()
                        except OSError:
                            pass
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except OSError:
                            pass
            if stdout_thread is not None:
                stdout_thread.join(timeout=1.0)
            if stderr_thread is not None:
                stderr_thread.join(timeout=1.0)
            _close_windows_job(job)

    # Inputs not assigned a protocol result after a clean empty solve have no
    # outcomes; otherwise every requested input has an explicit result.
    return [result if result is not None else {"timeout": True} for result in results]
