from typing import Dict
from app.core.config import config
from app.schemas.email import EmailSettings
from .storage.base import StorageProvider
from .storage.cloudinary_provider import CloudinaryProvider

from .payment.base import PaymentProvider
from .payment.stripe_provider import StripeProvider
from .email.base import EmailProvider
from .email.smtp_provider import SMTPProvider
from .email.null_provider import NullEmailProvider

STORAGE_PROVIDERS: Dict[str, StorageProvider] = {}
PAYMENT_PROVIDERS: Dict[str, PaymentProvider] = {}
EMAIL_PROVIDERS: Dict[str, EmailProvider] = {}


def _create_email_settings() -> EmailSettings:
    """Create EmailSettings from app config."""
    return EmailSettings(
        provider=config.EMAIL_PROVIDER or "smtp",
        host=config.EMAIL_HOST,
        port=config.EMAIL_PORT,
        username=config.EMAIL_USERNAME,
        password=config.EMAIL_PASSWORD,
        from_address=config.EMAIL_FROM,
        use_tls=config.EMAIL_USE_TLS,
        use_ssl=config.EMAIL_USE_SSL,
        timeout_seconds=config.EMAIL_TIMEOUT_SECONDS,
    )


def register_providers():
    STORAGE_PROVIDERS["cloudinary"] = CloudinaryProvider()
    PAYMENT_PROVIDERS["stripe"] = StripeProvider()

    settings = _create_email_settings()
    provider_name = (config.EMAIL_PROVIDER or "smtp").lower()

    if provider_name in ("smtp", "mailtrap"):
        EMAIL_PROVIDERS["default"] = SMTPProvider(settings)
    else:
        EMAIL_PROVIDERS["default"] = NullEmailProvider()


def get_storage_provider(name: str):
    return STORAGE_PROVIDERS.get(name)


def get_payment_provider(name: str):
    return PAYMENT_PROVIDERS.get(name)


def get_email_provider(name: str = "default"):
    return EMAIL_PROVIDERS.get(name)
