import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.models.requests import ProblemContext
from app.models.responses import HintResponse
from app.services.llm_client import GuidanceMode, LLMClient, LLMMessage, LLMRequest
from app.services.problem_catalog import ProblemCatalog

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)

MAX_CONTEXT_LENGTHS = {
    "statement": 12_000,
    "code": 12_000,
    "approach": 6_000,
    "error_message": 4_000,
}
MODE_LIMITS = {
    GuidanceMode.HINT: (20.0, 500),
    GuidanceMode.VALIDATE: (25.0, 700),
    GuidanceMode.DEBUG: (20.0, 600),
    GuidanceMode.JOURNAL_REVIEW: (20.0, 500),
}
PROMPT_FILENAMES = {
    GuidanceMode.HINT: "hint.md",
    GuidanceMode.VALIDATE: "validate.md",
    GuidanceMode.DEBUG: "debug.md",
    GuidanceMode.JOURNAL_REVIEW: "journal_review.md",
}
CODE_FENCE_PATTERN = re.compile(r"```")
SOLUTION_SIGNATURE_PATTERN = re.compile(
    r"\b(?:def|function)\s+(?:solve|solution)\s*\(", re.IGNORECASE
)


class GuidanceServiceError(RuntimeError):
    """Raised when structured guidance cannot be safely produced."""


class GuidancePolicyError(ValueError):
    """Raised when a model response violates Unstuck's learner-first policy."""


@dataclass(frozen=True)
class GuidanceResult(Generic[ResponseModel]):
    response: ResponseModel
    truncated_fields: tuple[str, ...]


class GuidanceService:
    def __init__(self, *, client: LLMClient, catalog: ProblemCatalog) -> None:
        self._client = client
        self._catalog = catalog

    def generate(
        self,
        *,
        mode: GuidanceMode,
        context: ProblemContext,
        response_model: type[ResponseModel],
        requested_hint_level: int | None = None,
        previous_hint_levels: list[int] | None = None,
    ) -> GuidanceResult[ResponseModel]:
        context_payload, truncated_fields = self._prepare_context(context)
        request = self._build_request(
            mode=mode,
            context_payload=context_payload,
            response_model=response_model,
            requested_hint_level=requested_hint_level,
            previous_hint_levels=previous_hint_levels or [],
        )

        try:
            response = self._validate_response(
                self._client.generate(request), response_model, mode, requested_hint_level
            )
        except (GuidancePolicyError, ValidationError):
            retry_request = replace(
                request,
                messages=(
                    *request.messages,
                    LLMMessage(
                        role="developer",
                        content=(
                            "Your previous response did not satisfy the required response schema "
                            "or Unstuck hint policy. Return only a JSON object that follows the "
                            "and requested guidance level."
                        ),
                    ),
                ),
            )
            try:
                response = self._validate_response(
                    self._client.generate(
                        retry_request
                    ),
                    response_model,
                    mode,
                    requested_hint_level,
                )
            except (GuidancePolicyError, ValidationError) as retry_error:
                raise GuidanceServiceError(
                    "The guidance response could not be validated. Please try again."
                ) from retry_error

        return GuidanceResult(response=response, truncated_fields=truncated_fields)

    def _build_request(
        self,
        *,
        mode: GuidanceMode,
        context_payload: dict[str, Any],
        response_model: type[BaseModel],
        requested_hint_level: int | None,
        previous_hint_levels: list[int],
    ) -> LLMRequest:
        timeout_seconds, max_output_tokens = MODE_LIMITS[mode]
        developer_prompt = self._load_prompt(mode)
        request_details = {
            "problem_context": context_payload,
            "requested_hint_level": requested_hint_level,
            "previous_hint_levels": previous_hint_levels,
        }
        return LLMRequest(
            mode=mode,
            messages=(
                LLMMessage(role="developer", content=developer_prompt),
                LLMMessage(
                    role="user",
                    content=json.dumps(request_details, ensure_ascii=False, sort_keys=True),
                ),
            ),
            response_schema=response_model.model_json_schema(),
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )

    def _prepare_context(self, context: ProblemContext) -> tuple[dict[str, Any], tuple[str, ...]]:
        context_payload = context.model_dump(mode="json")
        truncated_fields: list[str] = []
        for field_name, max_length in MAX_CONTEXT_LENGTHS.items():
            value = context_payload.get(field_name)
            if isinstance(value, str) and len(value) > max_length:
                context_payload[field_name] = (
                    f"{value[:max_length]}\n[truncated by Unstuck before guidance generation]"
                )
                truncated_fields.append(field_name)

        if context.slug:
            catalog_problem = self._catalog.get(context.slug)
            if catalog_problem:
                context_payload["catalog_facts"] = {
                    "difficulty": catalog_problem.difficulty,
                    "patterns": catalog_problem.patterns,
                    "prerequisites": catalog_problem.prerequisites,
                    "constraints": catalog_problem.constraints,
                }
            else:
                context_payload["catalog_facts"] = "unknown slug"
        else:
            context_payload["catalog_facts"] = "no catalog entry supplied"

        return context_payload, tuple(truncated_fields)

    @staticmethod
    def _validate_response(
        payload: dict[str, Any],
        response_model: type[ResponseModel],
        mode: GuidanceMode,
        requested_hint_level: int | None,
    ) -> ResponseModel:
        response = response_model.model_validate(payload)
        if mode is GuidanceMode.HINT and isinstance(response, HintResponse):
            if response.level != requested_hint_level:
                raise GuidancePolicyError("The response did not match the requested hint level.")
            GuidanceService._validate_hint_policy(response)
        return response

    @staticmethod
    def _validate_hint_policy(response: HintResponse) -> None:
        if response.level > 3:
            return
        content = "\n".join(part for part in [response.guidance, response.question] if part)
        if CODE_FENCE_PATTERN.search(content) or SOLUTION_SIGNATURE_PATTERN.search(content):
            raise GuidancePolicyError(
                "Hint levels 1 through 3 must not include solution-like code."
            )

    @staticmethod
    def _load_prompt(mode: GuidanceMode) -> str:
        prompt_path = Path(__file__).resolve().parents[1] / "prompts" / PROMPT_FILENAMES[mode]
        return prompt_path.read_text(encoding="utf-8")
