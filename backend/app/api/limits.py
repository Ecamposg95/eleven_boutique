"""Outermost guard for the admin API.

Caps request bodies: FastAPI reads declared bodies before running dependencies, and a multipart
upload spools to disk with no total limit. Also marks responses as private and not indexable.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.errors import ApiError

ADMIN_PREFIX = "/api/v1/admin"
MB = 1024 * 1024
DEFAULT_LIMIT = 2 * MB
# Per-file limits (20 MB) are enforced by the handlers; these bound the request as a whole.
ROUTE_LIMITS = {
    f"{ADMIN_PREFIX}/media": 220 * MB,
    f"{ADMIN_PREFIX}/imports/products/preview": 21 * MB,
}
MESSAGE = "La solicitud excede el tamaño permitido"


class AdminGuard:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "") if scope["type"] == "http" else ""
        if not path.startswith(ADMIN_PREFIX):
            await self.app(scope, receive, send)
            return

        limit = ROUTE_LIMITS.get(path.rstrip("/"), DEFAULT_LIMIT)
        headers = dict(scope["headers"])
        declared = headers.get(b"content-length", b"")
        if declared.isdigit() and int(declared) > limit:
            await _reject(send)
            return

        received = 0

        async def limited_receive() -> Message:
            # Content-Length can be absent (chunked) or false, so the stream is counted too.
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise ApiError(413, "body_too_large", MESSAGE)
            return message

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers["Cache-Control"] = "no-store"
                response_headers["X-Robots-Tag"] = "noindex"
            await send(message)

        await self.app(scope, limited_receive, private_send)


async def _reject(send: Send) -> None:
    body = ('{"error":{"code":"body_too_large","message":"' + MESSAGE + '"}}').encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"connection", b"close"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
