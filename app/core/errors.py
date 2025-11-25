from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import HTTPException, status


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


def http_error(
    code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Raise a standardized HTTP error with consistent JSON shape.

    The final response body will be::

        {"code": "ERROR_CODE", "message": "Human message", "details": {...}}

    Use this from services and routers to keep errors consistent.
    """
    payload = ErrorResponse(code=code, message=message, details=details).model_dump()
    raise HTTPException(status_code=status_code, detail=payload)


def bad_request(
    code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> None:
    http_error(code, message, status.HTTP_400_BAD_REQUEST, details)


def unauthorized(
    code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> None:
    http_error(code, message, status.HTTP_401_UNAUTHORIZED, details)


def forbidden(
    code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> None:
    http_error(code, message, status.HTTP_403_FORBIDDEN, details)


def not_found(
    code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> None:
    http_error(code, message, status.HTTP_404_NOT_FOUND, details)


def conflict(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    http_error(code, message, status.HTTP_409_CONFLICT, details)


def unprocessable(
    code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> None:
    http_error(code, message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


def internal_error(
    code: str = "INTERNAL_SERVER_ERROR",
    message: str = "Internal server error",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    http_error(code, message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)
