from typing import Dict
from .cloudinary_provider import CloudinaryProvider

PROVIDERS: Dict[str, CloudinaryProvider] = {}


def register_providers():
    PROVIDERS["cloudinary"] = CloudinaryProvider()


def get_provider(name: str):
    return PROVIDERS.get(name)
