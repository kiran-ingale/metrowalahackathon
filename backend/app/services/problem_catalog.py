import json
from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from app.models.catalog import CatalogProblem

KNOWN_PATTERNS = frozenset(
    {
        "array",
        "hash-map",
        "string",
        "two-pointers",
        "sliding-window",
        "binary-search",
        "stack",
        "tree",
        "depth-first-search",
        "breadth-first-search",
        "graph",
        "dynamic-programming",
    }
)


class CatalogValidationError(ValueError):
    """Raised when curated problem metadata violates catalog invariants."""


class ProblemCatalog:
    def __init__(self, problems: Iterable[CatalogProblem]) -> None:
        self._problems = {problem.slug: problem for problem in problems}

    @classmethod
    def from_file(cls, path: Path) -> "ProblemCatalog":
        try:
            raw_problems = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CatalogValidationError(f"Catalog file was not found: {path}") from error
        except json.JSONDecodeError as error:
            raise CatalogValidationError(f"Catalog file is not valid JSON: {path}") from error

        if not isinstance(raw_problems, list):
            raise CatalogValidationError("Catalog root must be a JSON array.")

        try:
            problems = [CatalogProblem.model_validate(raw_problem) for raw_problem in raw_problems]
        except ValidationError as error:
            raise CatalogValidationError(f"Catalog entry is invalid: {error}") from error

        cls._validate(problems)
        return cls(problems)

    @staticmethod
    def _validate(problems: list[CatalogProblem]) -> None:
        slugs = [problem.slug for problem in problems]
        if len(slugs) != len(set(slugs)):
            raise CatalogValidationError("Catalog contains duplicate slugs.")

        known_slugs = set(slugs)
        for problem in problems:
            unknown_patterns = set(problem.patterns) - KNOWN_PATTERNS
            if unknown_patterns:
                raise CatalogValidationError(
                    f"Problem '{problem.slug}' uses unknown patterns: {sorted(unknown_patterns)}."
                )

            referenced_slugs = [*problem.prerequisites, *problem.related_slugs]
            missing_slugs = set(referenced_slugs) - known_slugs
            if missing_slugs:
                raise CatalogValidationError(
                    f"Problem '{problem.slug}' references missing slugs: {sorted(missing_slugs)}."
                )

        prerequisites_by_slug = {
            problem.slug: problem.prerequisites for problem in problems
        }
        ProblemCatalog._validate_prerequisite_graph(prerequisites_by_slug)

    @staticmethod
    def _validate_prerequisite_graph(prerequisites_by_slug: dict[str, list[str]]) -> None:
        visited: set[str] = set()
        active: set[str] = set()

        def visit(slug: str) -> None:
            if slug in active:
                raise CatalogValidationError(
                    f"Catalog contains a circular prerequisite chain at '{slug}'."
                )
            if slug in visited:
                return

            active.add(slug)
            for prerequisite in prerequisites_by_slug[slug]:
                visit(prerequisite)
            active.remove(slug)
            visited.add(slug)

        for slug in prerequisites_by_slug:
            visit(slug)

    def get(self, slug: str) -> CatalogProblem | None:
        return self._problems.get(slug)

    def __len__(self) -> int:
        return len(self._problems)

    def values(self) -> tuple[CatalogProblem, ...]:
        return tuple(self._problems.values())


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "problems.json"


def load_default_catalog() -> ProblemCatalog:
    return ProblemCatalog.from_file(default_catalog_path())
