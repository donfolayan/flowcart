import smtplib
from email.message import EmailMessage as StdEmailMessage
from email.utils import make_msgid
from typing import Optional

from .base import EmailMessage, EmailProvider, EmailSendError
from app.schemas.email import EmailSettings


class SMTPProvider(EmailProvider):
    """
    Generic SMTP email provider supporting STARTTLS and SSL.
    Works with common SMTP services (Mailtrap, Gmail, SendGrid, SES, etc.).
    """

    def __init__(self, settings: EmailSettings):
        self.settings = settings

    def _build_message(self, message: EmailMessage) -> StdEmailMessage:
        message.ensure_body()

        msg = StdEmailMessage()
        msg["Subject"] = message.subject
        msg["From"] = self.settings.from_address or self.settings.username or ""
        msg["To"] = ", ".join(message.to)
        msg["Message-Id"] = make_msgid()

        for key, value in message.headers.items():
            msg[key] = value

        if message.text_body:
            msg.set_content(message.text_body)

        if message.html_body:
            msg.add_alternative(message.html_body, subtype="html")

        return msg

    def send(self, message: EmailMessage) -> Optional[str]:
        msg = self._build_message(message)

        host = self.settings.host
        if not host:
            raise EmailSendError("EMAIL_HOST is not configured")

        try:
            if self.settings.use_ssl:
                smtp = smtplib.SMTP_SSL(
                    host,
                    self.settings.port,
                    timeout=self.settings.timeout_seconds,
                )
            else:
                smtp = smtplib.SMTP(
                    host,
                    self.settings.port,
                    timeout=self.settings.timeout_seconds,
                )
            with smtp as server:
                if self.settings.use_tls and not self.settings.use_ssl:
                    server.starttls()
                if self.settings.username and self.settings.password:
                    server.login(self.settings.username, self.settings.password)
                failures = server.send_message(msg)
        except Exception as exc:  # noqa: BLE001
            raise EmailSendError(f"Failed to send email: {exc}") from exc

        if failures:
            raise EmailSendError(f"Failed recipients: {list(failures.keys())}")

        return msg.get("Message-Id")
