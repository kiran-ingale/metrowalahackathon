import json
import logging
from pathlib import Path

import pytest

from app.core.errors import log_unhandled_exception
from app.models.requests import ProblemContext
from app.models.responses import ApproachFeedback, ApproachStatus
from app.services.counterexamples.oracles import TwoSumAdapter
from app.services.counterexamples.runner import SafePythonRunner
from app.services.guidance import GuidanceService
from app.services.llm_client import FixtureLLMClient, GuidanceMode
from app.services.problem_catalog import ProblemCatalog, default_catalog_path

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "evaluations"


def load_fixture(name: str) -> list[dict[str, object]]:
    return json.loads((FIXTURES_DIRECTORY / name).read_text(encoding="utf-8"))


def catalog() -> ProblemCatalog:
    return ProblemCatalog.from_file(default_catalog_path())


def test_guidance_evaluation_fixtures_cover_cataloged_classifications() -> None:
    fixtures = load_fixture("guidance_cases.v1.json")
    statuses = set()

    assert len(fixtures) >= 20
    for fixture in fixtures:
        context = ProblemContext.model_validate(fixture["context"])
        expected = fixture["expected"]
        response = fixture["fixture_response"]
        service = GuidanceService(
            client=FixtureLLMClient({GuidanceMode.VALIDATE: [response]}),
            catalog=catalog(),
        )

        result = service.generate(
            mode=GuidanceMode.VALIDATE,
            context=context,
            response_model=ApproachFeedback,
        ).response

        assert catalog().get(context.slug or "") is not None
        assert result.status.value == expected["status"]
        assert result.verification.value == expected["verification"]
        statuses.add(result.status)

    assert statuses == {
        ApproachStatus.VALID,
        ApproachStatus.VALID_BUT_INEFFICIENT,
        ApproachStatus.FUNDAMENTALLY_FLAWED,
        ApproachStatus.INSUFFICIENT_CONTEXT,
    }


@pytest.mark.counterexample_eval
@pytest.mark.parametrize("fixture", load_fixture("two_sum_wrong_candidates.v1.json"))
def test_known_wrong_candidates_produce_reproducible_counterexamples(
    fixture: dict[str, object],
) -> None:
    adapter = TwoSumAdapter()
    runner = SafePythonRunner()
    source = fixture["source"]
    input_data = fixture["reproducible_input"]
    assert isinstance(source, str)
    assert isinstance(input_data, dict)
    expected = adapter.oracle(input_data)

    first_run = runner.run_source(source, input_data)
    second_run = runner.run_source(source, input_data)

    assert first_run.is_success
    assert second_run.is_success
    assert not adapter.outputs_match(input_data, expected, first_run.output)
    assert first_run.output == second_run.output


def test_unhandled_error_logging_omits_secrets_and_user_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "sk-test-secret"
    raw_code = "def solve(input_data): return journal_prompt"

    with caplog.at_level(logging.ERROR):
        log_unhandled_exception("request-123", RuntimeError(f"{secret} {raw_code}"))

    assert secret not in caplog.text
    assert raw_code not in caplog.text
    assert "RuntimeError" in caplog.text
