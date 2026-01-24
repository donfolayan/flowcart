import pytest

from app.core.email.base import EmailMessage, EmailSendError
from app.core.email.helpers import send_email
from app.core.email.null_provider import NullEmailProvider
from app.core.registry import EMAIL_PROVIDERS


def test_email_message_requires_body():
    msg = EmailMessage(to=["user@example.com"], subject="Hello")
    with pytest.raises(ValueError):
        msg.ensure_body()


def test_send_email_raises_when_no_provider_registered():
    # Backup and clear providers
    backup = dict(EMAIL_PROVIDERS)
    try:
        EMAIL_PROVIDERS.clear()
        msg = EmailMessage(to=["user@example.com"], subject="Hello", text_body="Hi")
        with pytest.raises(EmailSendError):
            send_email(msg)
    finally:
        EMAIL_PROVIDERS.clear()
        EMAIL_PROVIDERS.update(backup)


def test_send_email_with_null_provider_returns_none():
    # Backup providers and register the null provider
    backup = dict(EMAIL_PROVIDERS)
    try:
        EMAIL_PROVIDERS.clear()
        EMAIL_PROVIDERS["default"] = NullEmailProvider()
        msg = EmailMessage(
            to=["user@example.com"],
            subject="Hello",
            text_body="Hi there",
        )
        result = send_email(msg)
        assert result is None
    finally:
        EMAIL_PROVIDERS.clear()
        EMAIL_PROVIDERS.update(backup)
