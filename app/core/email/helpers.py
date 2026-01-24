from .base import EmailMessage, EmailSendError
from app.core.registry import get_email_provider


def send_email(message: EmailMessage):
    """Send using the configured provider; raise if none configured."""
    provider = get_email_provider()
    if not provider:
        raise EmailSendError("No email provider is registered")
    return provider.send(message)
