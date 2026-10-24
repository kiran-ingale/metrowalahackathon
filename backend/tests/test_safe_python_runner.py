from app.services.counterexamples.models import ExecutionRequest, ExecutionStatus
from app.services.counterexamples.runner import MAX_STDIO_BYTES, SafePythonRunner


def run_candidate(source: str, input_data: object = [1, 2, 3]):
    return SafePythonRunner(timeout_seconds=0.2).run(
        ExecutionRequest(source=source, input_data=input_data)
    )


def test_runner_executes_one_solve_call_and_normalizes_json_output() -> None:
    result = run_candidate(
        "def solve(input_data):\n    return {'sum': sum(input_data), 'items': input_data}\n"
    )

    assert result.status is ExecutionStatus.SUCCESS
    assert result.output == {"sum": 6, "items": [1, 2, 3]}
    assert result.isolation_notes


def test_runner_reports_candidate_exceptions() -> None:
    result = run_candidate("def solve(input_data):\n    raise ValueError('bad input')\n")

    assert result.status is ExecutionStatus.RUNTIME_ERROR
    assert result.error == "solve raised ValueError"


def test_runner_times_out_infinite_loop() -> None:
    result = run_candidate("def solve(input_data):\n    while True:\n        pass\n")

    assert result.status is ExecutionStatus.TIMEOUT


def test_runner_rejects_non_json_output() -> None:
    result = run_candidate("def solve(input_data):\n    return {1, 2, 3}\n")

    assert result.status is ExecutionStatus.INVALID_OUTPUT


def test_runner_requires_solve_function() -> None:
    result = run_candidate("def other(input_data):\n    return input_data\n")

    assert result.status is ExecutionStatus.CONTRACT_ERROR
    assert result.error == "Candidate must define solve(input_data)."


def test_runner_caps_candidate_stdout() -> None:
    source = "def solve(input_data):\n    print('x' * 10000)\n    return input_data\n"
    result = run_candidate(source)

    assert result.status is ExecutionStatus.SUCCESS
    assert len(result.stdout) == MAX_STDIO_BYTES


def test_runner_does_not_allow_environment_imports() -> None:
    result = run_candidate(
        "import os\ndef solve(input_data):\n    return os.environ.get('OPENAI_API_KEY')\n"
    )

    assert result.status is ExecutionStatus.CONTRACT_ERROR
    assert "Imports" in (result.error or "")
