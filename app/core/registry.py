from typing import Dict
from .storage.cloudinary_provider import CloudinaryProvider
from .storage.base import StorageProvider

PROVIDERS: Dict[str, StorageProvider] = {}


def register_providers():
    PROVIDERS["cloudinary"] = CloudinaryProvider()


def get_provider(name: str):
    return PROVIDERS.get(name)
