from types import SimpleNamespace

from app.api.routes_counterexamples import find_counterexample
from app.main import create_app
from app.models.requests import CounterexampleRequest, ProblemContext, ProgrammingLanguage
from app.models.responses import CounterexampleStatus
from app.services.counterexamples.generators import generate_two_sum_cases
from app.services.counterexamples.oracles import TwoSumAdapter
from app.services.counterexamples.service import CounterexampleService
from app.services.counterexamples.shrinker import shrink_two_sum
from app.services.problem_catalog import ProblemCatalog, default_catalog_path

CORRECT_TWO_SUM = """\
def solve(input_data):
    seen = {}
    for index, value in enumerate(input_data['nums']):
        complement = input_data['target'] - value
        if complement in seen:
            return [seen[complement], index]
        seen[value] = index
    return None
"""

WRONG_TWO_SUM = """\
def solve(input_data):
    return [0, 1]
"""


def counterexample_request(
    source: str,
    slug: str = "two-sum",
    language: ProgrammingLanguage = ProgrammingLanguage.PYTHON,
) -> CounterexampleRequest:
    return CounterexampleRequest(
        context=ProblemContext(
            slug=slug,
            title="Two Sum",
            statement="Return indices of two values that add to target.",
            language=language,
            code=source,
        ),
        confirm_execution=True,
    )


def service() -> CounterexampleService:
    return CounterexampleService(ProblemCatalog.from_file(default_catalog_path()), case_limit=8)


def test_two_sum_oracle_matches_official_examples() -> None:
    assert TwoSumAdapter().verify_oracle()


def test_generator_is_deterministic_for_recorded_seed() -> None:
    assert generate_two_sum_cases(123, 8) == generate_two_sum_cases(123, 8)


def test_correct_two_sum_returns_none_found_for_bounded_cases() -> None:
    response = service().find(counterexample_request(CORRECT_TWO_SUM))

    assert response.status is CounterexampleStatus.NONE_FOUND
    assert response.cases_tried == 8
    assert response.seed is not None


def test_wrong_two_sum_returns_a_reproducible_minimized_mismatch() -> None:
    counterexample_service = service()
    response = counterexample_service.find(counterexample_request(WRONG_TWO_SUM))

    assert response.status is CounterexampleStatus.FOUND
    assert response.input is not None
    assert response.expected is not None or response.actual is not None
    fresh_run = counterexample_service._run_case(WRONG_TWO_SUM, response.input)
    assert fresh_run is not None
    assert not fresh_run.matches


def test_candidate_timeout_or_runtime_error_cannot_be_verified() -> None:
    timeout_source = "def solve(input_data):\n    while True:\n        pass\n"
    timeout = service().find(counterexample_request(timeout_source))
    runtime_error = service().find(
        counterexample_request("def solve(input_data):\n    raise ValueError('bad')\n")
    )

    assert timeout.status is CounterexampleStatus.COULD_NOT_VERIFY
    assert runtime_error.status is CounterexampleStatus.COULD_NOT_VERIFY


def test_unsupported_language_and_problem_fail_closed() -> None:
    class ExplodingRunner:
        def run_source(self, source: str, input_data: object) -> object:
            raise AssertionError("Unsupported requests must not execute source.")

    counterexample_service = CounterexampleService(
        ProblemCatalog.from_file(default_catalog_path()), runner=ExplodingRunner()
    )
    unsupported_language = counterexample_service.find(
        counterexample_request(WRONG_TWO_SUM, language=ProgrammingLanguage.JAVASCRIPT)
    )
    unsupported_problem = counterexample_service.find(
        counterexample_request(WRONG_TWO_SUM, slug="binary-search")
    )

    assert unsupported_language.status is CounterexampleStatus.NOT_SUPPORTED
    assert unsupported_language.cases_tried == 0
    assert unsupported_problem.status is CounterexampleStatus.NOT_SUPPORTED
    assert unsupported_problem.cases_tried == 0


def test_shrinker_keeps_a_two_sum_mismatch() -> None:
    source = WRONG_TWO_SUM
    counterexample_service = service()
    original = {"nums": [1, 2, 3, 10], "target": 6}

    def mismatches(input_data: dict[str, object]) -> bool:
        run = counterexample_service._run_case(source, input_data)
        return run is not None and not run.matches

    shrunk = shrink_two_sum(original, mismatches)

    assert len(shrunk["nums"]) <= len(original["nums"])
    assert mismatches(shrunk)


def test_counterexample_endpoint_is_opt_in_and_returns_service_result() -> None:
    app = create_app(counterexample_service=service())
    request = SimpleNamespace(app=app, state=SimpleNamespace(request_id="request-123"))

    response = find_counterexample(counterexample_request(WRONG_TWO_SUM), request)

    assert response.status is CounterexampleStatus.FOUND
