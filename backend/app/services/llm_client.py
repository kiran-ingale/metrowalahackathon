import json
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from openai import OpenAI
from pydantic import SecretStr


class GuidanceMode(StrEnum):
    HINT = "hint"
    VALIDATE = "validate"
    DEBUG = "debug"
    JOURNAL_REVIEW = "journal_review"


class LLMClientError(RuntimeError):
    """Raised when an LLM provider cannot return a usable structured payload."""


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMRequest:
    mode: GuidanceMode
    messages: tuple[LLMMessage, ...]
    response_schema: dict[str, Any]
    timeout_seconds: float
    max_output_tokens: int


class LLMClient(Protocol):
    def generate(self, request: LLMRequest) -> dict[str, Any]:
        """Return a parsed JSON object that can be validated by the caller."""


class FixtureLLMClient:
    """Deterministic client for tests and local UI development."""

    def __init__(
        self, responses: Mapping[GuidanceMode, Sequence[dict[str, Any] | Exception]]
    ) -> None:
        self._responses = {
            mode: deque(mode_responses) for mode, mode_responses in responses.items()
        }
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> dict[str, Any]:
        self.requests.append(request)
        try:
            result = self._responses[request.mode].popleft()
        except (KeyError, IndexError) as error:
            raise LLMClientError(
                f"No fixture response is configured for '{request.mode}'."
            ) from error

        if isinstance(result, Exception):
            raise result
        return result


class UnconfiguredLLMClient:
    """Fails safely until server-only OpenAI configuration is supplied."""

    def generate(self, _: LLMRequest) -> dict[str, Any]:
        raise LLMClientError("The OpenAI client is not configured.")


class OpenAIResponsesClient:
    """Production adapter using the OpenAI Responses API structured-output format."""

    def __init__(self, *, api_key: SecretStr, model: str) -> None:
        if not model.strip():
            raise ValueError("An OpenAI model must be configured.")
        self._client = OpenAI(api_key=api_key.get_secret_value())
        self._model = model

    def generate(self, request: LLMRequest) -> dict[str, Any]:
        developer_instructions = "\n\n".join(
            message.content for message in request.messages if message.role == "developer"
        )
        user_input = "\n\n".join(
            message.content for message in request.messages if message.role != "developer"
        )
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=developer_instructions,
                input=user_input,
                max_output_tokens=request.max_output_tokens,
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": f"unstuck_{request.mode}_response",
                        "schema": request.response_schema,
                        "strict": False,
                    }
                },
                timeout=request.timeout_seconds,
            )
        except Exception as error:  # Provider failures are normalized at this boundary.
            raise LLMClientError("The OpenAI request failed.") from error

        return self._parse_output_text(response.output_text)

    @staticmethod
    def _parse_output_text(output_text: str | None) -> dict[str, Any]:
        if not output_text:
            raise LLMClientError("The OpenAI response did not include structured output text.")
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as error:
            raise LLMClientError("The OpenAI response was not valid JSON.") from error
        if not isinstance(payload, dict):
            raise LLMClientError("The OpenAI response must be a JSON object.")
        return payload
