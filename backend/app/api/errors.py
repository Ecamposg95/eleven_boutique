import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)

CODES = {404: "not_found", 405: "method_not_allowed", 422: "validation_error"}
DEFAULT_MESSAGES = {404: "Recurso no encontrado", 405: "Método no permitido"}


class ApiError(HTTPException):
    """An HTTP error with a stable machine-readable code, e.g. 409 brand_unpublished."""

    def __init__(self, status: int, code: str, message: str, headers=None) -> None:
        super().__init__(status_code=status, detail=message, headers=headers)
        self.code = code


def _error(status: int, code: str, message: str, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        status = exc.status_code
        code = getattr(exc, "code", None) or CODES.get(status, HTTPStatus(status).name.lower())
        # The router's own 404/405 carry Starlette's English reason phrase.
        message = str(exc.detail)
        if message == HTTPStatus(status).phrase:
            message = DEFAULT_MESSAGES.get(status, message)
        return _error(status, code, message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        parts = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return _error(422, CODES[422], "; ".join(parts) or "Solicitud inválida")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return _error(500, "internal_error", "Error interno del servidor")
