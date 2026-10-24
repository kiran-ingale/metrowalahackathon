from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ProgrammingLanguage(StrEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"
    OTHER = "other"


class SubmissionVerdict(StrEnum):
    COMPILE_ERROR = "compile_error"
    RUNTIME_ERROR = "runtime_error"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT = "time_limit"
    ACCEPTED = "accepted"


class ProblemExample(BaseModel):
    input: str = Field(min_length=1, max_length=10_000)
    output: str = Field(min_length=1, max_length=10_000)
    explanation: str | None = Field(default=None, max_length=10_000)


class ProblemContext(BaseModel):
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=300)
    statement: str = Field(min_length=1, max_length=50_000)
    examples: list[ProblemExample] = Field(default_factory=list, max_length=20)
    constraints: list[str] = Field(default_factory=list, max_length=50)
    language: ProgrammingLanguage = ProgrammingLanguage.OTHER
    code: str | None = Field(default=None, max_length=50_000)
    approach: str | None = Field(default=None, max_length=20_000)
    verdict: SubmissionVerdict | None = None
    error_message: str | None = Field(default=None, max_length=20_000)


class HintRequest(BaseModel):
    context: ProblemContext
    level: int = Field(ge=1, le=4)
    previous_hint_levels: list[int] = Field(default_factory=list, max_length=4)


class ApproachValidationRequest(BaseModel):
    context: ProblemContext

    @model_validator(mode="after")
    def require_code_or_approach(self) -> "ApproachValidationRequest":
        if not self.context.code and not self.context.approach:
            raise ValueError("Provide code or a description of the approach.")
        return self


class DebugRequest(BaseModel):
    context: ProblemContext

    @model_validator(mode="after")
    def require_verdict_or_error(self) -> "DebugRequest":
        if not self.context.verdict and not self.context.error_message:
            raise ValueError("Provide a submission verdict or error message.")
        return self


class CounterexampleRequest(BaseModel):
    context: ProblemContext
    confirm_execution: Literal[True]

    @model_validator(mode="after")
    def require_candidate_code(self) -> "CounterexampleRequest":
        if not self.context.code:
            raise ValueError("Provide candidate code to search for a counterexample.")
        return self
