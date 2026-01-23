"""Logging dependencies and middleware for request tracing."""

import logging
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to store request_id across async calls
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add request_id to all logs within a request context."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request_id
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in context variable
        request_id_ctx.set(request_id)

        # Add to request state for access in route handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request_id to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class RequestIdFilter(logging.Filter):
    """Logging filter that adds request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("")
        return True


def get_logger(name: str = "app") -> logging.Logger:
    """Get a logger with request_id filter attached."""
    logger = logging.getLogger(name)

    # Add the filter if not already present
    if not any(isinstance(f, RequestIdFilter) for f in logger.filters):
        logger.addFilter(RequestIdFilter())

    return logger
