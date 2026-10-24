import logging
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.responses import ApiErrorResponse

logger = logging.getLogger(__name__)


def request_id_for(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def api_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    retryable: bool,
) -> JSONResponse:
    error = ApiErrorResponse(
        code=code,
        message=message,
        request_id=request_id,
        retryable=retryable,
    )
    return JSONResponse(status_code=status_code, content=error.model_dump())


async def validation_exception_handler(request: Request, _: RequestValidationError) -> JSONResponse:
    return api_error_response(
        status_code=422,
        code="invalid_request",
        message="The request payload is invalid.",
        request_id=request_id_for(request),
        retryable=False,
    )


def log_unhandled_exception(request_id: str, error: Exception) -> None:
    """Log only safe operational metadata, never untrusted exception text or tracebacks."""
    logger.error(
        "Unhandled application error type=%s request_id=%s", type(error).__name__, request_id
    )


async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
    request_id = request_id_for(request)
    log_unhandled_exception(request_id, error)
    return api_error_response(
        status_code=500,
        code="internal_server_error",
        message="An unexpected error occurred.",
        request_id=request_id,
        retryable=True,
    )
