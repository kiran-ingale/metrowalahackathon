from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.errors import api_error_response, request_id_for


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, max_body_size: int) -> None:
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return api_error_response(
                status_code=413,
                code="request_too_large",
                message="The request payload exceeds the allowed size.",
                request_id=request_id_for(request),
                retryable=False,
            )
        return await call_next(request)
