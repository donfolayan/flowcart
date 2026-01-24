import logging
from typing import Optional

from .base import EmailMessage, EmailProvider

logger = logging.getLogger(__name__)


class NullEmailProvider(EmailProvider):
    """No-op provider useful for local/dev when email is disabled."""

    def send(self, message: EmailMessage) -> Optional[str]:
        logger.info(
            "Email sending skipped (null provider). Subject=%s, To=%s",
            message.subject,
            message.to,
        )
        return None
