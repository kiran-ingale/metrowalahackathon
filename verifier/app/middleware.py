"""HTTP middleware for request-size enforcement."""

from collections import deque

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_size: int = 1024 * 1024) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.max_body_size:
            await self._send_too_large(send)
            return

        # Buffer before calling the app, so a body that exceeds the limit cannot
        # trigger an inner exception handler after it has already started a 500.
        messages: deque[Message] = deque()
        received_size = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.request":
                received_size += len(message.get("body", b""))
                if received_size > self.max_body_size:
                    await self._send_too_large(send)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        async def buffered_receive() -> Message:
            if messages:
                return messages.popleft()
            return await receive()

        await self.app(scope, buffered_receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None
        return None

    @staticmethod
    async def _send_too_large(send: Send) -> None:
        body = b'{"detail":"Request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
