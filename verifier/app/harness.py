"""Isolated child-process entry point for candidate execution.

The parent launches this file with ``python -I`` and sends one JSON request on
stdin. Candidate output is discarded; only JSON written through the duplicated
protocol stdout handle reaches the parent.
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import sys
from typing import Any, Callable

try:
    import resource
except ImportError:  # Windows
    resource = None  # type: ignore[assignment]

try:
    import signal
except ImportError:  # pragma: no cover - signal exists on supported Python builds
    signal = None  # type: ignore[assignment]


_MEMORY_LIMIT = 256 * 1024 * 1024
_RECURSION_LIMIT = 3_000


def _error_text(error: BaseException) -> str:
    try:
        message = str(error)
    except BaseException:
        message = "<unprintable exception>"
    return f"{type(error).__name__}: {message}"


def _quiet_streams(devnull: Any) -> None:
    """Reassert output suppression before each piece of candidate code runs."""
    sys.stdout = devnull
    sys.stderr = devnull
    sys.__stdout__ = devnull
    sys.__stderr__ = devnull
    # Silence native writes and children started with os.system as well.
    for fd in (1, 2):
        try:
            os.dup2(devnull.fileno(), fd)
        except OSError:
            pass


def _set_limits(per_case_timeout: float, n: int) -> None:
    if resource is None:
        return
    try:
        if hasattr(resource, "RLIMIT_AS"):
            resource.setrlimit(resource.RLIMIT_AS, (_MEMORY_LIMIT, _MEMORY_LIMIT))
        if hasattr(resource, "RLIMIT_CPU"):
            cpu_seconds = max(2, math.ceil(max(per_case_timeout, 0.01) * max(n, 1)) + 1)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    except (OSError, ValueError):
        # Some POSIX hosts expose resource but disallow changing one of these
        # limits. The parent still enforces wall and per-case timeouts.
        pass


def _call_with_timer(call: Callable[[], Any], timeout: float) -> Any:
    timer_armed = False
    if (
        signal is not None
        and os.name != "nt"
        and hasattr(signal, "setitimer")
        and hasattr(signal, "ITIMER_REAL")
        and hasattr(signal, "SIGALRM")
    ):
        try:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            signal.setitimer(signal.ITIMER_REAL, max(float(timeout), 0.001))
            timer_armed = True
        except (OSError, ValueError):
            timer_armed = False
    try:
        return call()
    finally:
        if timer_armed:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
            except (OSError, ValueError):
                pass


def _write_json(protocol_stdout: Any, value: Any, *, index: int | None = None) -> None:
    try:
        line = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except BaseException as error:
        failure: dict[str, Any] = {"err": _error_text(error)}
        if index is not None:
            failure["i"] = index
        line = json.dumps(failure, ensure_ascii=False, separators=(",", ":"))
    protocol_stdout.write(line + "\n")
    protocol_stdout.flush()


def _solve(request: dict[str, Any], protocol_stdout: Any, devnull: Any) -> None:
    inputs = request.get("inputs", [])
    method = request.get("method", "")
    per_case_timeout = float(request.get("per_case_timeout", 1.0))
    namespace: dict[str, Any] = {}
    solution = None
    setup_error: BaseException | None = None

    try:
        _quiet_streams(devnull)
        exec(compile(request.get("code", ""), "<candidate>", "exec"), namespace)
        _quiet_streams(devnull)
        solution = namespace["Solution"]()
    except BaseException as error:
        setup_error = error

    for index, args in enumerate(inputs):
        if setup_error is not None:
            _write_json(protocol_stdout, {"i": index, "err": _error_text(setup_error)}, index=index)
            continue
        try:
            _quiet_streams(devnull)
            copied_args = copy.deepcopy(args)
            result = _call_with_timer(
                lambda: getattr(solution, method)(**copied_args), per_case_timeout
            )
            _write_json(protocol_stdout, {"i": index, "ok": result}, index=index)
        except BaseException as error:
            _write_json(protocol_stdout, {"i": index, "err": _error_text(error)}, index=index)


def _generate(request: dict[str, Any], protocol_stdout: Any, devnull: Any) -> None:
    per_case_timeout = float(request.get("per_case_timeout", 1.0))
    n = max(0, int(request.get("n", 0)))
    size = int(request.get("size", 0))
    seed = int(request.get("seed", 0))
    namespace: dict[str, Any] = {}
    try:
        _quiet_streams(devnull)
        exec(compile(request.get("code", ""), "<generator>", "exec"), namespace)
        generator = namespace["gen"]
        generated = []
        for index in range(n):
            _quiet_streams(devnull)
            args = _call_with_timer(
                lambda index=index: generator(random.Random(seed + index), size),
                per_case_timeout,
            )
            if not isinstance(args, dict):
                raise TypeError("gen(rng, size) must return an args dict")
            generated.append(args)
        _write_json(protocol_stdout, generated)
    except BaseException as error:
        _write_json(protocol_stdout, {"err": _error_text(error)})


def main() -> int:
    # Duplicate stdout before touching streams or executing user code. The
    # duplicate remains connected to the parent even after fd 1 is silenced.
    protocol_stdout = os.fdopen(
        os.dup(sys.stdout.fileno()), "w", encoding="utf-8", buffering=1
    )
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise TypeError("request must be a JSON object")
    except BaseException as error:
        _write_json(protocol_stdout, {"err": _error_text(error)})
        return 2

    devnull = open(os.devnull, "w", encoding="utf-8")
    _quiet_streams(devnull)
    try:
        sys.setrecursionlimit(_RECURSION_LIMIT)
        _set_limits(
            float(request.get("per_case_timeout", 1.0)),
            int(request.get("n", len(request.get("inputs", [])))),
        )
        mode = request.get("mode")
        if mode == "solve":
            _solve(request, protocol_stdout, devnull)
        elif mode == "gen":
            _generate(request, protocol_stdout, devnull)
        else:
            _write_json(protocol_stdout, {"err": "ValueError: unsupported mode"})
            return 2
    finally:
        devnull.close()
        protocol_stdout.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
