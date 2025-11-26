from .product import ProductResponse, ProductCreate, ProductUpdate  # noqa: F401,F403
from .category import (
    CategoryResponse,
    CategoryCreate,
    CategoryUpdate,
    CategoryMinimalResponse,
)  # noqa: F401,F403
from .media import MediaResponse  # noqa: F401,F403
from .order import OrderResponse, OrderCreate, OrderUpdate, OrderPreviewResponse  # noqa: F401,F403
from .order_item import OrderItemResponse  # noqa: F401,F403

try:
    ProductResponse.model_rebuild()
    ProductCreate.model_rebuild()
    ProductUpdate.model_rebuild()
except NameError:
    pass

try:
    CategoryResponse.model_rebuild()
    CategoryCreate.model_rebuild()
    CategoryUpdate.model_rebuild()
    CategoryMinimalResponse.model_rebuild()
except NameError:
    pass

try:
    MediaResponse.model_rebuild()
except NameError:
    pass

try:
    OrderResponse.model_rebuild()
    OrderCreate.model_rebuild()
    OrderUpdate.model_rebuild()
    OrderPreviewResponse.model_rebuild()
    OrderItemResponse.model_rebuild()
except NameError:
    pass

__all__ = [
    "ProductResponse",
    "ProductCreate",
    "ProductUpdate",
    "CategoryResponse",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryMinimalResponse",
    "MediaResponse",
    "OrderResponse",
    "OrderCreate",
    "OrderUpdate",
    "OrderPreviewResponse",
    "OrderItemResponse",
]
