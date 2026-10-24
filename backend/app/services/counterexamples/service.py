"""Verified, bounded counterexample searches for explicitly supported adapters."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.catalog import CounterexampleSupport
from app.models.requests import CounterexampleRequest, ProgrammingLanguage
from app.models.responses import CounterexampleResponse, CounterexampleStatus
from app.services.counterexamples.generators import (
    DEFAULT_CASE_LIMIT,
    DEFAULT_SEED,
    generate_two_sum_cases,
)
from app.services.counterexamples.oracles import TwoSumAdapter
from app.services.counterexamples.runner import SafePythonRunner
from app.services.counterexamples.shrinker import shrink_two_sum
from app.services.problem_catalog import ProblemCatalog


@dataclass(frozen=True)
class CandidateRun:
    expected: object
    actual: object
    matches: bool


class CounterexampleService:
    """Search small deterministic cases without claiming proof of correctness."""

    def __init__(
        self,
        catalog: ProblemCatalog,
        runner: SafePythonRunner | None = None,
        seed: int = DEFAULT_SEED,
        case_limit: int = DEFAULT_CASE_LIMIT,
    ) -> None:
        self.catalog = catalog
        self.runner = runner or SafePythonRunner()
        self.seed = seed
        self.case_limit = case_limit
        self.two_sum = TwoSumAdapter()
        self.oracle_available = self.two_sum.verify_oracle()

    def find(self, request: CounterexampleRequest) -> CounterexampleResponse:
        problem = self.catalog.get(request.context.slug or "")
        if request.context.language is not ProgrammingLanguage.PYTHON:
            return self._not_supported("Counterexample search currently supports Python only.")
        if problem is None or problem.counterexample_support is not CounterexampleSupport.PYTHON:
            return self._not_supported(
                "This problem does not have a verified counterexample adapter."
            )
        if problem.slug != self.two_sum.slug:
            return self._not_supported(
                "This problem does not have a verified counterexample adapter."
            )
        if not self.oracle_available:
            return CounterexampleResponse(
                status=CounterexampleStatus.COULD_NOT_VERIFY,
                explanation="The trusted oracle failed its verification examples.",
                cases_tried=0,
                seed=self.seed,
            )

        for case_number, input_data in enumerate(
            generate_two_sum_cases(self.seed, self.case_limit), start=1
        ):
            run = self._run_case(request.context.code, input_data)
            if run is None:
                return CounterexampleResponse(
                    status=CounterexampleStatus.COULD_NOT_VERIFY,
                    explanation=(
                        "Candidate execution could not be verified on generated "
                        f"case {case_number}."
                    ),
                    cases_tried=case_number,
                    seed=self.seed,
                )
            if not run.matches:
                return self._found_response(request.context.code, input_data, case_number)

        return CounterexampleResponse(
            status=CounterexampleStatus.NONE_FOUND,
            explanation="No mismatch was found within the bounded deterministic search.",
            cases_tried=self.case_limit,
            seed=self.seed,
        )

    def _found_response(
        self, source: str, input_data: dict[str, object], cases_tried: int
    ) -> CounterexampleResponse:
        def still_mismatches(candidate_input: dict[str, object]) -> bool:
            run = self._run_case(source, candidate_input)
            return run is not None and not run.matches

        minimized_input = shrink_two_sum(input_data, still_mismatches)
        final_run = self._run_case(source, minimized_input)
        if final_run is None or final_run.matches:
            return CounterexampleResponse(
                status=CounterexampleStatus.COULD_NOT_VERIFY,
                explanation="The mismatch could not be reproduced after minimization.",
                cases_tried=cases_tried,
                seed=self.seed,
            )
        return CounterexampleResponse(
            status=CounterexampleStatus.FOUND,
            input=minimized_input,
            expected=final_run.expected,
            actual=final_run.actual,
            explanation=(
                "The minimized input reproduces a mismatch with the trusted Two Sum oracle."
            ),
            cases_tried=cases_tried,
            minimized=minimized_input != input_data,
            seed=self.seed,
        )

    def _run_case(self, source: str, input_data: dict[str, object]) -> CandidateRun | None:
        oracle_result = self.runner.run_source(self.two_sum.oracle_source(), input_data)
        candidate_result = self.runner.run_source(source, input_data)
        if not oracle_result.is_success or not candidate_result.is_success:
            return None
        return CandidateRun(
            expected=oracle_result.output,
            actual=candidate_result.output,
            matches=self.two_sum.outputs_match(
                input_data, oracle_result.output, candidate_result.output
            ),
        )

    def _not_supported(self, explanation: str) -> CounterexampleResponse:
        return CounterexampleResponse(
            status=CounterexampleStatus.NOT_SUPPORTED,
            explanation=explanation,
            cases_tried=0,
            seed=self.seed,
        )
