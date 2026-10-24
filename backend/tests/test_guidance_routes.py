from types import SimpleNamespace

from fastapi import Response
from fastapi.responses import JSONResponse

from app.api.routes_guidance import create_hint, explain_error, validate_approach
from app.core.settings import Settings
from app.main import create_app
from app.models.requests import (
    ApproachValidationRequest,
    DebugRequest,
    HintRequest,
    ProblemContext,
    ProgrammingLanguage,
    SubmissionVerdict,
)
from app.models.responses import (
    ApproachFeedback,
    ApproachStatus,
    DebugResponse,
    HintResponse,
    VerificationStatus,
)
from app.services.guidance import GuidanceResult, GuidanceService
from app.services.llm_client import FixtureLLMClient, GuidanceMode
from app.services.problem_catalog import ProblemCatalog, default_catalog_path


class StubGuidanceService:
    def __init__(self, result: GuidanceResult[object]) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def generate(self, **kwargs: object) -> GuidanceResult[object]:
        self.calls.append(kwargs)
        return self.result


def problem_context(**overrides: object) -> ProblemContext:
    values: dict[str, object] = {
        "slug": "two-sum",
        "title": "Two Sum",
        "statement": "Find two elements that add to a target.",
        "language": ProgrammingLanguage.PYTHON,
    }
    values.update(overrides)
    return ProblemContext(**values)


def app_request(service: object) -> SimpleNamespace:
    application = create_app(
        Settings(openai_api_key=None, allowed_origins=["http://localhost:5173"]),
        guidance_service=service,
    )
    return SimpleNamespace(app=application, state=SimpleNamespace(request_id="request-123"))


def test_hint_endpoint_returns_requested_guidance_and_truncation_header() -> None:
    guidance = HintResponse(
        level=1,
        title="Think about earlier values",
        guidance="What information from earlier elements would be useful?",
        full_solution_included=False,
    )
    service = StubGuidanceService(
        GuidanceResult(response=guidance, truncated_fields=("statement",))
    )
    response = Response()

    result = create_hint(
        HintRequest(context=problem_context(), level=1),
        app_request(service),
        response,
    )

    assert result == guidance
    assert response.headers["X-Unstuck-Truncated-Fields"] == "statement"
    assert service.calls[0]["mode"] is GuidanceMode.HINT


def test_validation_endpoint_returns_structured_feedback() -> None:
    feedback = ApproachFeedback(
        status=ApproachStatus.VALID_BUT_INEFFICIENT,
        summary="The nested loops are logically correct.",
        reasoning="They inspect every candidate pair.",
        verification=VerificationStatus.NOT_RUN,
    )
    service = StubGuidanceService(GuidanceResult(response=feedback, truncated_fields=()))

    result = validate_approach(
        ApproachValidationRequest(context=problem_context(approach="Check every pair.")),
        app_request(service),
        Response(),
    )

    assert result == feedback
    assert service.calls[0]["mode"] is GuidanceMode.VALIDATE


def test_debug_endpoint_preserves_actual_error_context() -> None:
    debug_response = DebugResponse(
        summary="The result differs on at least one case.",
        reasoning="The reported verdict is a wrong answer, not a runtime error.",
        next_check="Trace the first duplicate value.",
    )
    service = StubGuidanceService(GuidanceResult(response=debug_response, truncated_fields=()))

    result = explain_error(
        DebugRequest(
            context=problem_context(verdict=SubmissionVerdict.WRONG_ANSWER)
        ),
        app_request(service),
        Response(),
    )

    assert result == debug_response
    assert service.calls[0]["mode"] is GuidanceMode.DEBUG


def test_malformed_provider_response_returns_safe_api_error() -> None:
    catalog = ProblemCatalog.from_file(default_catalog_path())
    service = GuidanceService(
        client=FixtureLLMClient({GuidanceMode.HINT: [{"level": 1}, {"level": 1}]}),
        catalog=catalog,
    )

    result = create_hint(
        HintRequest(context=problem_context(), level=1),
        app_request(service),
        Response(),
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 502
    assert b'"code":"guidance_response_invalid"' in result.body


def test_counterexample_claim_is_rejected_before_runner_exists() -> None:
    feedback = ApproachFeedback(
        status=ApproachStatus.FUNDAMENTALLY_FLAWED,
        summary="The assumption skips valid pairs.",
        reasoning="A counterexample is not available in this endpoint yet.",
        verification=VerificationStatus.COUNTEREXAMPLE_FOUND,
    )
    service = StubGuidanceService(GuidanceResult(response=feedback, truncated_fields=()))

    result = validate_approach(
        ApproachValidationRequest(context=problem_context(approach="Only compare neighbors.")),
        app_request(service),
        Response(),
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 502
    assert b'"code":"guidance_response_invalid"' in result.body
