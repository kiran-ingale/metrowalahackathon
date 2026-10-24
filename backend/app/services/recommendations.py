from collections.abc import Iterable

from app.models.catalog import (
    CatalogProblem,
    ProblemRecommendation,
    RecommendationCategory,
    RecommendationsResponse,
)
from app.services.problem_catalog import ProblemCatalog

DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}


class RecommendationService:
    def __init__(self, catalog: ProblemCatalog) -> None:
        self._catalog = catalog

    def recommend(
        self,
        *,
        current_slug: str,
        solved_slugs: Iterable[str] = (),
        dismissed_slugs: Iterable[str] = (),
        weak_patterns: Iterable[str] = (),
    ) -> RecommendationsResponse | None:
        current_problem = self._catalog.get(current_slug)
        if current_problem is None:
            return None

        solved = set(solved_slugs)
        dismissed = set(dismissed_slugs)
        excluded = solved | dismissed | {current_slug}
        weak_pattern_set = set(weak_patterns)
        recommendations: list[ProblemRecommendation] = []

        prerequisite = self._first_eligible_prerequisite(current_problem, excluded)
        if prerequisite:
            recommendations.append(
                self._to_recommendation(
                    problem=prerequisite,
                    current_problem=current_problem,
                    category=RecommendationCategory.PREREQUISITE,
                )
            )
            excluded.add(prerequisite.slug)

        related_problem = self._first_eligible_related_problem(
            current_problem,
            excluded,
            weak_pattern_set,
        )
        if related_problem:
            recommendations.append(
                self._to_recommendation(
                    problem=related_problem,
                    current_problem=current_problem,
                    category=RecommendationCategory.RELATED,
                )
            )

        return RecommendationsResponse(
            recommendations=recommendations,
            basis=(
                "Recommendations use the curated problem catalog and supplied local learning "
                "history."
                if solved or dismissed or weak_pattern_set
                else (
                    "Recommendations use the curated problem catalog because learning history "
                    "is unavailable."
                )
            ),
        )

    def _first_eligible_prerequisite(
        self, current_problem: CatalogProblem, excluded: set[str]
    ) -> CatalogProblem | None:
        for slug in current_problem.prerequisites:
            if slug not in excluded:
                return self._catalog.get(slug)
        return None

    def _first_eligible_related_problem(
        self,
        current_problem: CatalogProblem,
        excluded: set[str],
        weak_patterns: set[str],
    ) -> CatalogProblem | None:
        explicit_candidates = [
            self._catalog.get(slug)
            for slug in current_problem.related_slugs
            if slug not in excluded
        ]
        catalog_candidates = [
            problem
            for problem in self._catalog.values()
            if problem.slug not in excluded
            and problem.slug not in current_problem.prerequisites
            and set(problem.patterns).intersection(current_problem.patterns)
        ]
        explicit_candidates = [candidate for candidate in explicit_candidates if candidate]
        candidates = explicit_candidates or catalog_candidates
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda problem: (
                not bool(set(problem.patterns).intersection(weak_patterns)),
                DIFFICULTY_ORDER[problem.difficulty],
                problem.slug,
            ),
        )

    @staticmethod
    def _to_recommendation(
        *,
        problem: CatalogProblem,
        current_problem: CatalogProblem,
        category: RecommendationCategory,
    ) -> ProblemRecommendation:
        shared_patterns = sorted(set(problem.patterns).intersection(current_problem.patterns))
        if category is RecommendationCategory.PREREQUISITE:
            explanation = (
                f"Reinforces {problem.patterns[0]} before returning to {current_problem.title}."
            )
        else:
            shared_pattern = shared_patterns[0] if shared_patterns else problem.patterns[0]
            explanation = f"Builds on the {shared_pattern} idea used in {current_problem.title}."

        return ProblemRecommendation(
            slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            patterns=problem.patterns,
            category=category,
            explanation=explanation,
        )
