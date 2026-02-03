import os
import secrets
from typing import Optional
from fastapi import Cookie, Response, HTTPException, status

SESSION_COOKIE_NAME = "session_id"
DEFAULT_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def generate_session_id() -> str:
    return secrets.token_urlsafe(32)


async def get_or_create_session_id(
    response: Response,
    session_id: Optional[str] = Cookie(None),
) -> str:
    """
    Ensure a session_id exists. If missing, generate one and set cookie.
    - response: FastAPI Response, used to set cookie when generating new session_id.
    - session_id: incoming cookie value (if any).
    Returns a session_id string.
    """
    secure_cookie: Optional[bool] = None
    max_age: int = DEFAULT_MAX_AGE

    if secure_cookie is None:
        env = os.getenv("FASTAPI_ENV", os.getenv("ENV", "production"))
        secure_cookie = env.lower() != "development"

    if session_id:
        if not (4 <= len(session_id) <= 128):
            raise HTTPException(status_code=400, detail="Invalid session cookie")
        return session_id

    # create new session id and set cookie
    session_id = generate_session_id()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    return session_id


async def get_session_id(
    session_id: Optional[str] = Cookie(None),
) -> Optional[str]:
    """Retrieve session_id from cookie if it exists."""
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID cookie is missing",
        )
    return session_id
