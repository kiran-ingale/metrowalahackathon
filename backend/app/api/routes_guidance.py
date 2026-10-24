from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.core.errors import api_error_response, request_id_for
from app.models.requests import ApproachValidationRequest, DebugRequest, HintRequest
from app.models.responses import (
    ApproachFeedback,
    DebugResponse,
    HintResponse,
    VerificationStatus,
)
from app.services.guidance import GuidanceResult, GuidanceService, GuidanceServiceError
from app.services.llm_client import GuidanceMode, LLMClientError

router = APIRouter(prefix="/v1/guidance", tags=["guidance"])


def get_guidance_service(request: Request) -> GuidanceService:
    return request.app.state.guidance_service


def add_truncation_header(response: Response, result: GuidanceResult[object]) -> None:
    if result.truncated_fields:
        response.headers["X-Unstuck-Truncated-Fields"] = ",".join(result.truncated_fields)


def guidance_error_response(request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, GuidanceServiceError):
        return api_error_response(
            status_code=502,
            code="guidance_response_invalid",
            message="Guidance could not be validated. Please try again.",
            request_id=request_id_for(request),
            retryable=True,
        )
    return api_error_response(
        status_code=503,
        code="guidance_unavailable",
        message="Guidance is temporarily unavailable. Please try again.",
        request_id=request_id_for(request),
        retryable=True,
    )


@router.post("/hint", response_model=HintResponse)
def create_hint(
    payload: HintRequest, request: Request, response: Response
) -> HintResponse | JSONResponse:
    try:
        result = get_guidance_service(request).generate(
            mode=GuidanceMode.HINT,
            context=payload.context,
            response_model=HintResponse,
            requested_hint_level=payload.level,
            previous_hint_levels=payload.previous_hint_levels,
        )
    except (GuidanceServiceError, LLMClientError) as error:
        return guidance_error_response(request, error)

    add_truncation_header(response, result)
    return result.response


@router.post("/validate", response_model=ApproachFeedback)
def validate_approach(
    payload: ApproachValidationRequest, request: Request, response: Response
) -> ApproachFeedback | JSONResponse:
    try:
        result = get_guidance_service(request).generate(
            mode=GuidanceMode.VALIDATE,
            context=payload.context,
            response_model=ApproachFeedback,
        )
        if result.response.verification is VerificationStatus.COUNTEREXAMPLE_FOUND:
            raise GuidanceServiceError(
                "Approach validation cannot claim a counterexample before Module 07."
            )
    except (GuidanceServiceError, LLMClientError) as error:
        return guidance_error_response(request, error)

    add_truncation_header(response, result)
    return result.response


@router.post("/debug", response_model=DebugResponse)
def explain_error(
    payload: DebugRequest, request: Request, response: Response
) -> DebugResponse | JSONResponse:
    try:
        result = get_guidance_service(request).generate(
            mode=GuidanceMode.DEBUG,
            context=payload.context,
            response_model=DebugResponse,
        )
    except (GuidanceServiceError, LLMClientError) as error:
        return guidance_error_response(request, error)

    add_truncation_header(response, result)
    return result.response
