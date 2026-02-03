from typing import cast, Callable

from fastapi import FastAPI, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.errors import ErrorResponse
from app.core.logs.logging_utils import get_logger

logger = get_logger("app.exception_handlers")


async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else None,
        },
    )
    payload = ErrorResponse(
        code="INTERNAL_SERVER_ERROR", message="Internal server error"
    ).model_dump()
    return JSONResponse(status_code=500, content=payload)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle request validation errors."""
    # Cast to RequestValidationError for type safety
    validation_exc = cast(RequestValidationError, exc)
    logger.warning(
        "Request validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": validation_exc.errors(),
        },
    )
    payload = ErrorResponse(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": validation_exc.errors()},
    ).model_dump()
    return JSONResponse(status_code=422, content=jsonable_encoder(payload))


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Normalize all HTTPException details into the ErrorResponse JSON shape."""
    # Cast to HTTPException for type safety
    http_exc = cast(HTTPException, exc)
    logger.warning(
        "HTTP exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": http_exc.status_code,
            "detail": http_exc.detail,
        },
    )

    detail = http_exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        content = detail
    else:
        msg = detail if isinstance(detail, str) else str(detail)
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(http_exc.status_code, f"HTTP_{http_exc.status_code}")
        content = ErrorResponse(code=code, message=msg).model_dump()

    return JSONResponse(status_code=http_exc.status_code, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""
    app.add_exception_handler(Exception, handle_unhandled_exception)
    app.add_exception_handler(RequestValidationError, cast(Callable, validation_exception_handler))
    app.add_exception_handler(HTTPException, cast(Callable, http_exception_handler))
