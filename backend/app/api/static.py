from pathlib import PurePosixPath

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

SERVED_SUFFIXES = {".jpg", ".png", ".webp"}


class MediaFiles(StaticFiles):
    """Serves only what the image pipeline writes. Names are random, so files never change."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        if PurePosixPath(path).suffix not in SERVED_SUFFIXES:
            raise HTTPException(status_code=404)
        response = await super().get_response(path, scope)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
