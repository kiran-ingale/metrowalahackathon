from enum import StrEnum

from pydantic import BaseModel, Field


class Difficulty(StrEnum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class CounterexampleSupport(StrEnum):
    PYTHON = "python"
    PLANNED = "planned"
    NOT_SUPPORTED = "not_supported"


class CatalogProblem(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=300)
    difficulty: Difficulty
    patterns: list[str] = Field(min_length=1, max_length=10)
    prerequisites: list[str] = Field(default_factory=list, max_length=10)
    related_slugs: list[str] = Field(default_factory=list, max_length=10)
    constraints: list[str] = Field(default_factory=list, max_length=50)
    counterexample_support: CounterexampleSupport


class ProblemMetadataResponse(BaseModel):
    slug: str
    title: str
    difficulty: Difficulty
    patterns: list[str]
    prerequisites: list[str]
    related_slugs: list[str]
    constraints: list[str]

    @classmethod
    def from_catalog_problem(cls, problem: CatalogProblem) -> "ProblemMetadataResponse":
        return cls(
            slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            patterns=problem.patterns,
            prerequisites=problem.prerequisites,
            related_slugs=problem.related_slugs,
            constraints=problem.constraints,
        )


class RecommendationCategory(StrEnum):
    PREREQUISITE = "prerequisite"
    RELATED = "related"


class ProblemRecommendation(BaseModel):
    slug: str
    title: str
    difficulty: Difficulty
    patterns: list[str]
    category: RecommendationCategory
    explanation: str


class RecommendationsResponse(BaseModel):
    recommendations: list[ProblemRecommendation] = Field(max_length=2)
    basis: str
