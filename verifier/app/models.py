from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CounterexampleRequest(StrictModel):
    slug: str
    statement: str
    code: str


class CounterexampleResponse(StrictModel):
    status: Literal[
        "found",
        "crash",
        "timeout",
        "no_mismatch",
        "could_not_verify",
        "not_supported",
    ]
    trust_label: Literal[
        "verified_counterexample",
        "likely_counterexample",
        "could_not_verify",
        "examples_checked",
        "ai_guidance",
        "constraint_assessment",
    ]
    input: dict[str, Any] | None
    expected: Any | None
    got: Any | None
    tests_run: int
    seed: int
    minimized: bool
    reproduced: bool
    limitations: list[str]
    message: str
