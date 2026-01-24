import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple

from app.core.email import send_email, EmailMessage


def generate_verification_token() -> str:
    """Generate a secure random verification token."""
    return secrets.token_urlsafe(32)


def create_verification_token_expiry(hours: int = 24) -> datetime:
    """Create expiry datetime (default 24 hours from now)."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


async def send_verification_email(
    user_email: str,
    verification_token: str,
    app_url: str = "https://yourapp.com",
) -> None:
    """
    Send verification email with a magic link.
    
    Args:
        user_email: Recipient email address
        verification_token: The token to include in the verification link
        app_url: Base URL of your application (default: https://yourapp.com)
    """
    import asyncio
    
    verification_link = f"{app_url}/verify-email?token={verification_token}"
    
    message = EmailMessage(
        to=[user_email],
        subject="Verify your email",
        text_body=f"Click to verify your email: {verification_link}",
        html_body=f"""
        <p>Click the link below to verify your email:</p>
        <a href="{verification_link}">Verify Email</a>
        <p>This link expires in 24 hours.</p>
        """,
    )
    
    # Run blocking email send in thread pool
    await asyncio.to_thread(send_email, message)


async def send_and_save_verification_email(
    user,
    session,
    app_url: str = "https://yourapp.com",
) -> Tuple[str, datetime]:
    """
    Generate verification token, save to user, send email.
    
    Args:
        user: User model instance
        session: AsyncSession for database
        app_url: Base URL of your application
        
    Returns:
        Tuple of (verification_token, expiry_datetime)
    """
    token = generate_verification_token()
    expiry = create_verification_token_expiry(hours=24)
    
    user.verification_token = token
    user.verification_token_expires = expiry
    await session.commit()
    
    await send_verification_email(user.email, token, app_url)
    
    return token, expiry
