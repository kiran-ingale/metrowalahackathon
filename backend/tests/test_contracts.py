import pytest
from pydantic import ValidationError

from app.models.requests import (
    ApproachValidationRequest,
    CounterexampleRequest,
    DebugRequest,
    ProblemContext,
    ProgrammingLanguage,
    SubmissionVerdict,
)
from app.models.responses import ApiErrorResponse, HintResponse


def problem_context(**overrides: object) -> ProblemContext:
    values: dict[str, object] = {
        "title": "Two Sum",
        "statement": "Find two numbers that add to a target.",
        "language": ProgrammingLanguage.PYTHON,
    }
    values.update(overrides)
    return ProblemContext(**values)


def test_approach_validation_requires_code_or_approach() -> None:
    with pytest.raises(ValidationError):
        ApproachValidationRequest(context=problem_context())


def test_debug_request_accepts_actual_submission_result() -> None:
    request = DebugRequest(
        context=problem_context(verdict=SubmissionVerdict.WRONG_ANSWER)
    )

    assert request.context.verdict is SubmissionVerdict.WRONG_ANSWER


def test_counterexample_request_requires_explicit_execution_consent() -> None:
    with pytest.raises(ValidationError):
        CounterexampleRequest(
            context=problem_context(code="def solve(input_data): return input_data")
        )


def test_hint_response_rejects_a_full_solution_flag() -> None:
    with pytest.raises(ValidationError):
        HintResponse(
            level=1,
            title="Think about visited values",
            guidance="What information from earlier elements could help?",
            full_solution_included=True,
        )


def test_api_error_response_has_a_stable_contract() -> None:
    error = ApiErrorResponse(
        code="invalid_request",
        message="The request payload is invalid.",
        request_id="request-123",
        retryable=False,
    )

    assert error.model_dump()["request_id"] == "request-123"
