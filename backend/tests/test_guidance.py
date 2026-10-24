import pytest

from app.models.requests import ProblemContext, ProgrammingLanguage
from app.models.responses import ApproachFeedback, ApproachStatus, HintResponse
from app.services.guidance import GuidancePolicyError, GuidanceService, GuidanceServiceError
from app.services.llm_client import (
    FixtureLLMClient,
    GuidanceMode,
    LLMClientError,
    OpenAIResponsesClient,
)
from app.services.problem_catalog import ProblemCatalog, default_catalog_path


def problem_context(**overrides: object) -> ProblemContext:
    values: dict[str, object] = {
        "slug": "two-sum",
        "title": "Two Sum",
        "statement": "Find two elements that add to the target.",
        "language": ProgrammingLanguage.PYTHON,
    }
    values.update(overrides)
    return ProblemContext(**values)


def hint_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "level": 1,
        "title": "Think about previous values",
        "guidance": "What information from earlier elements would help you decide quickly?",
        "question": "What would you need to remember while scanning?",
        "revealed_concepts": ["visited values"],
        "full_solution_included": False,
    }
    payload.update(overrides)
    return payload


def guidance_service(responses: dict[GuidanceMode, list[dict[str, object] | Exception]]) -> tuple[
    GuidanceService, FixtureLLMClient
]:
    fixture_client = FixtureLLMClient(responses)
    return (
        GuidanceService(
            client=fixture_client,
            catalog=ProblemCatalog.from_file(default_catalog_path()),
        ),
        fixture_client,
    )


def test_guidance_service_returns_valid_hint_with_catalog_context() -> None:
    service, fixture_client = guidance_service({GuidanceMode.HINT: [hint_payload()]})

    result = service.generate(
        mode=GuidanceMode.HINT,
        context=problem_context(),
        response_model=HintResponse,
        requested_hint_level=1,
    )

    assert result.response.level == 1
    assert result.truncated_fields == ()
    prompt_content = fixture_client.requests[0].messages[1].content
    assert "2 <= nums.length <= 10^4" in prompt_content


def test_guidance_service_retries_a_malformed_response_once() -> None:
    service, fixture_client = guidance_service(
        {GuidanceMode.HINT: [{"level": 1}, hint_payload()]}
    )

    result = service.generate(
        mode=GuidanceMode.HINT,
        context=problem_context(),
        response_model=HintResponse,
        requested_hint_level=1,
    )

    assert result.response.title == "Think about previous values"
    assert len(fixture_client.requests) == 2


def test_guidance_service_returns_safe_error_after_retry_failure() -> None:
    service, _ = guidance_service({GuidanceMode.HINT: [{"level": 1}, {"level": 1}]})

    with pytest.raises(GuidanceServiceError):
        service.generate(
            mode=GuidanceMode.HINT,
            context=problem_context(),
            response_model=HintResponse,
            requested_hint_level=1,
        )


def test_hint_policy_rejects_solution_like_level_one_content() -> None:
    service, _ = guidance_service(
        {
            GuidanceMode.HINT: [
                hint_payload(guidance="```python\ndef solve(values):\n    return values\n```"),
                hint_payload(guidance="```python\ndef solve(values):\n    return values\n```"),
            ]
        }
    )

    with pytest.raises(GuidanceServiceError):
        service.generate(
            mode=GuidanceMode.HINT,
            context=problem_context(),
            response_model=HintResponse,
            requested_hint_level=1,
        )


def test_guidance_service_marks_truncated_context_fields() -> None:
    service, fixture_client = guidance_service({GuidanceMode.HINT: [hint_payload()]})

    result = service.generate(
        mode=GuidanceMode.HINT,
        context=problem_context(statement="x" * 12_001),
        response_model=HintResponse,
        requested_hint_level=1,
    )

    assert result.truncated_fields == ("statement",)
    assert "truncated by Unstuck" in fixture_client.requests[0].messages[1].content


def test_openai_client_rejects_malformed_structured_output() -> None:
    with pytest.raises(LLMClientError):
        OpenAIResponsesClient._parse_output_text("not-json")


def test_guidance_policy_exception_is_specific() -> None:
    with pytest.raises(GuidancePolicyError):
        GuidanceService._validate_hint_policy(
            HintResponse(**hint_payload(guidance="```python\ndef solve():\n    pass\n```"))
        )


def test_approach_feedback_schema_is_accepted_by_guidance_service() -> None:
    service, _ = guidance_service(
        {
            GuidanceMode.VALIDATE: [
                {
                    "status": ApproachStatus.VALID_BUT_INEFFICIENT,
                    "summary": "The nested loops can find a pair.",
                    "reasoning": "Each pair is checked once, so the logic is complete.",
                    "estimated_time_complexity": "O(n^2)",
                    "estimated_space_complexity": "O(1)",
                    "constraint_assessment": "This may be too slow at the upper limit.",
                    "next_question": "Can you avoid checking the same values repeatedly?",
                    "verification": "not_run",
                }
            ]
        }
    )

    result = service.generate(
        mode=GuidanceMode.VALIDATE,
        context=problem_context(approach="Check every pair."),
        response_model=ApproachFeedback,
    )

    assert result.response.status is ApproachStatus.VALID_BUT_INEFFICIENT
