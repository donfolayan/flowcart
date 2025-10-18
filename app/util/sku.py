from uuid import uuid4


def generate_unique_sku(name: str) -> str:
    prefix = name[:3].upper()
    unique_id = uuid4().hex[:5].upper()
    return f"{prefix}-{unique_id}"
