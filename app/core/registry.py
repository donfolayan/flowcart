from typing import Dict
from .storage.base import StorageProvider
from .storage.cloudinary_provider import CloudinaryProvider

from .payment.base import PaymentProvider
from .payment.stripe_provider import StripeProvider

STORAGE_PROVIDERS: Dict[str, StorageProvider] = {}
PAYMENT_PROVIDERS: Dict[str, PaymentProvider] = {}


def register_providers():
    STORAGE_PROVIDERS["cloudinary"] = CloudinaryProvider()
    PAYMENT_PROVIDERS["stripe"] = StripeProvider()


def get_storage_provider(name: str):
    return STORAGE_PROVIDERS.get(name)


def get_payment_provider(name: str):
    return PAYMENT_PROVIDERS.get(name)
