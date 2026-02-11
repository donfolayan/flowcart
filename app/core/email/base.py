from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class EmailMessage(BaseModel):
    to: List[str]
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)

    def ensure_body(self) -> None:
        if not self.text_body and not self.html_body:
            raise ValueError("Either text_body or html_body must be provided")


class EmailSendError(Exception):
    """Raised when sending an email fails."""


class EmailProvider:
    def send(self, message: EmailMessage) -> Optional[str]:
        """
        Send an email. Returns a provider-specific message id if available.
        Implementations should raise EmailSendError on failure.
        """
        raise NotImplementedError
