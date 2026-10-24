from enum import StrEnum

from pydantic import BaseModel, Field


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    RUNTIME_ERROR = "runtime_error"
    INVALID_OUTPUT = "invalid_output"
    CONTRACT_ERROR = "contract_error"
    RUNNER_ERROR = "runner_error"


class ExecutionRequest(BaseModel):
    source: str = Field(min_length=1, max_length=50_000)
    input_data: object


class ExecutionResult(BaseModel):
    status: ExecutionStatus
    output: object | None = None
    error: str | None = Field(default=None, max_length=2_000)
    stdout: str = Field(default="", max_length=4_096)
    stderr: str = Field(default="", max_length=4_096)
    isolation_notes: list[str] = Field(default_factory=list, max_length=5)

    @property
    def is_success(self) -> bool:
        return self.status is ExecutionStatus.SUCCESS
