"""A deliberately narrow local runner for trusted development workflows.

This is not a production sandbox. It restricts the submitted language surface and
uses a separate process, but a public deployment needs operating-system or
container-level isolation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from math import ceil
from pathlib import Path
from textwrap import dedent

from app.services.counterexamples.models import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)

MAX_INPUT_BYTES = 20_000
MAX_STDIO_BYTES = 4_096
MAX_WRAPPER_OUTPUT_BYTES = 16_384
DEFAULT_TIMEOUT_SECONDS = 1.0
MAX_MEMORY_BYTES = 128 * 1024 * 1024

WRAPPER_SOURCE = dedent(
    """
    import ast
    import json
    import sys
    from pathlib import Path

    MAX_STDIO_BYTES = 4096
    DISALLOWED_NODES = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef)
    SAFE_BUILTINS = {
        "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
        "enumerate": enumerate, "float": float, "int": int, "len": len,
        "list": list, "max": max, "min": min, "range": range, "reversed": reversed,
        "print": print, "set": set, "sorted": sorted, "str": str, "sum": sum,
        "tuple": tuple, "ValueError": ValueError, "zip": zip,
    }

    class CappedTextStream:
        def __init__(self, limit):
            self.limit = limit
            self.parts = []
            self.size = 0

        def write(self, value):
            value = str(value)
            remaining = self.limit - self.size
            if remaining > 0:
                kept = value[:remaining]
                self.parts.append(kept)
                self.size += len(kept)
            return len(value)

        def flush(self):
            return None

        def value(self):
            return "".join(self.parts)

    def emit(payload):
        sys.__stdout__.write(json.dumps(payload, separators=(",", ":")))

    def normalize_json(value):
        try:
            encoded = json.dumps(value, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            return False, None
        return True, json.loads(encoded)

    def validate_source(source):
        try:
            tree = ast.parse(source, mode="exec")
        except SyntaxError as error:
            return "Invalid Python source: {}".format(error.msg)

        for node in ast.walk(tree):
            if isinstance(node, DISALLOWED_NODES):
                return "Imports, classes, and async functions are not allowed."
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return "Dunder attribute access is not allowed."
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                return "Dunder names are not allowed."
        return None

    def main():
        workspace = Path.cwd()
        source = (workspace / "candidate.py").read_text(encoding="utf-8")
        input_data = json.loads((workspace / "input.json").read_text(encoding="utf-8"))
        contract_error = validate_source(source)
        if contract_error:
            emit({"status": "contract_error", "error": contract_error})
            return

        stdout = CappedTextStream(MAX_STDIO_BYTES)
        stderr = CappedTextStream(MAX_STDIO_BYTES)
        namespace = {"__builtins__": SAFE_BUILTINS, "__name__": "candidate"}
        previous_stdout, previous_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = stdout, stderr
            exec(compile(source, "candidate.py", "exec"), namespace, namespace)
        except Exception as error:
            emit({
                "status": "contract_error",
                "error": "Candidate could not be loaded: {}".format(type(error).__name__),
                "stdout": stdout.value(),
                "stderr": stderr.value(),
            })
            return
        finally:
            sys.stdout, sys.stderr = previous_stdout, previous_stderr

        solve = namespace.get("solve")
        if not callable(solve):
            emit({"status": "contract_error", "error": "Candidate must define solve(input_data)."})
            return

        try:
            sys.stdout, sys.stderr = stdout, stderr
            output = solve(input_data)
        except Exception as error:
            emit({
                "status": "runtime_error",
                "error": "solve raised {}".format(type(error).__name__),
                "stdout": stdout.value(),
                "stderr": stderr.value(),
            })
            return
        finally:
            sys.stdout, sys.stderr = previous_stdout, previous_stderr

        is_json_compatible, normalized = normalize_json(output)
        if not is_json_compatible:
            emit({
                "status": "invalid_output",
                "error": "solve must return JSON-serializable data.",
                "stdout": stdout.value(),
                "stderr": stderr.value(),
            })
            return
        emit({
            "status": "success",
            "output": normalized,
            "stdout": stdout.value(),
            "stderr": stderr.value(),
        })

    if __name__ == "__main__":
        main()
    """
).strip()


class SafePythonRunner:
    """Execute a limited Python function once in a short-lived child process."""

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_input_bytes: int = MAX_INPUT_BYTES,
        max_wrapper_output_bytes: int = MAX_WRAPPER_OUTPUT_BYTES,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_input_bytes = max_input_bytes
        self.max_wrapper_output_bytes = max_wrapper_output_bytes

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        try:
            encoded_input = json.dumps(
                request.input_data, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError):
            return self._result(
                ExecutionStatus.INVALID_OUTPUT,
                error="Input data must be JSON-serializable.",
            )

        if len(encoded_input) > self.max_input_bytes:
            return self._result(
                ExecutionStatus.CONTRACT_ERROR,
                error="Input data exceeds the runner size limit.",
            )

        try:
            with tempfile.TemporaryDirectory(prefix="unstuck-run-") as temporary_directory:
                workspace = Path(temporary_directory)
                (workspace / "candidate.py").write_text(request.source, encoding="utf-8")
                (workspace / "input.json").write_bytes(encoded_input)
                (workspace / "runner.py").write_text(WRAPPER_SOURCE, encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, "-I", "-S", "runner.py"],
                    cwd=workspace,
                    env=self._sanitized_environment(),
                    capture_output=True,
                    preexec_fn=self._posix_resource_limits() if os.name == "posix" else None,
                    timeout=self.timeout_seconds,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            return self._result(
                ExecutionStatus.TIMEOUT,
                error="Candidate execution exceeded the time limit.",
            )
        except OSError as error:
            return self._result(
                ExecutionStatus.RUNNER_ERROR,
                error=f"The local execution process could not be started: {type(error).__name__}.",
            )

        if len(completed.stdout) > self.max_wrapper_output_bytes:
            return self._result(
                ExecutionStatus.RUNNER_ERROR,
                error="Runner output exceeded the size limit.",
            )
        if completed.returncode != 0:
            return self._result(
                ExecutionStatus.RUNNER_ERROR,
                error="The runner process exited unexpectedly.",
                stderr=self._decode_output(completed.stderr),
            )

        try:
            payload = json.loads(completed.stdout)
            result = ExecutionResult.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            return self._result(
                ExecutionStatus.RUNNER_ERROR,
                error="The runner returned an invalid execution result.",
                stderr=self._decode_output(completed.stderr),
            )
        return result.model_copy(update={"isolation_notes": self._isolation_notes()})

    def run_source(self, source: str, input_data: object) -> ExecutionResult:
        return self.run(ExecutionRequest(source=source, input_data=input_data))

    @staticmethod
    def _sanitized_environment() -> dict[str, str]:
        environment = {"PYTHONIOENCODING": "utf-8"}
        if os.name == "nt":
            environment["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\\Windows")
        return environment

    @staticmethod
    def _decode_output(output: bytes) -> str:
        return output[:MAX_STDIO_BYTES].decode("utf-8", errors="replace")

    def _posix_resource_limits(self):
        cpu_seconds = max(1, ceil(self.timeout_seconds))

        def apply_limits() -> None:
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))

        return apply_limits

    def _result(
        self,
        status: ExecutionStatus,
        *,
        error: str,
        stderr: str = "",
    ) -> ExecutionResult:
        return ExecutionResult(
            status=status,
            error=error,
            stderr=stderr,
            isolation_notes=self._isolation_notes(),
        )

    @staticmethod
    def _isolation_notes() -> list[str]:
        notes = [
            "Local-MVP runner only; public deployment requires container or VM isolation.",
            "Candidate imports and filesystem APIs are excluded by the supported contract.",
        ]
        if os.name == "nt":
            notes.append("Windows CPU and memory process limits are not applied by this runner.")
        else:
            notes.append("Unix child processes receive CPU and address-space limits.")
        return notes
