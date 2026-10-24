from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str
    version: str
    status: str


class VerificationStatus(StrEnum):
    NOT_RUN = "not_run"
    EXAMPLES_PASS = "examples_pass"
    COUNTEREXAMPLE_FOUND = "counterexample_found"
    COULD_NOT_VERIFY = "could_not_verify"


class HintResponse(BaseModel):
    level: int = Field(ge=1, le=4)
    title: str = Field(min_length=1, max_length=300)
    guidance: str = Field(min_length=1, max_length=10_000)
    question: str | None = Field(default=None, max_length=2_000)
    revealed_concepts: list[str] = Field(default_factory=list, max_length=20)
    full_solution_included: Literal[False] = False


class ApproachStatus(StrEnum):
    VALID = "valid"
    VALID_BUT_INEFFICIENT = "valid_but_inefficient"
    FUNDAMENTALLY_FLAWED = "fundamentally_flawed"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class ApproachFeedback(BaseModel):
    status: ApproachStatus
    summary: str = Field(min_length=1, max_length=5_000)
    reasoning: str = Field(min_length=1, max_length=10_000)
    estimated_time_complexity: str | None = Field(default=None, max_length=200)
    estimated_space_complexity: str | None = Field(default=None, max_length=200)
    constraint_assessment: str | None = Field(default=None, max_length=2_000)
    next_question: str | None = Field(default=None, max_length=2_000)
    optimization_suggestion: str | None = Field(default=None, max_length=2_000)
    verification: VerificationStatus = VerificationStatus.NOT_RUN


class DebugResponse(BaseModel):
    summary: str = Field(min_length=1, max_length=5_000)
    reasoning: str = Field(min_length=1, max_length=10_000)
    next_check: str = Field(min_length=1, max_length=2_000)
    assumptions: list[str] = Field(default_factory=list, max_length=20)


class JournalReviewResponse(BaseModel):
    summary: str = Field(min_length=1, max_length=5_000)
    corrections: list[str] = Field(default_factory=list, max_length=10)
    reflection_question: str = Field(min_length=1, max_length=2_000)


class CounterexampleStatus(StrEnum):
    FOUND = "found"
    NONE_FOUND = "none_found"
    NOT_SUPPORTED = "not_supported"
    COULD_NOT_VERIFY = "could_not_verify"


class CounterexampleResponse(BaseModel):
    status: CounterexampleStatus
    input: object | None = None
    expected: object | None = None
    actual: object | None = None
    explanation: str | None = Field(default=None, max_length=5_000)
    cases_tried: int = Field(ge=0)
    minimized: bool = False
    seed: int | None = None


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool
