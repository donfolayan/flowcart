import secrets
from datetime import datetime, timedelta, timezone


def generate_password_reset_token() -> str:
    """Generate a secure random password reset token."""
    return secrets.token_urlsafe(32)


def create_password_reset_token_expiry(hours: int = 1) -> datetime:
    """Create expiry datetime (default 1 hour from now)."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)
