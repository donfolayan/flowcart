"""
API v1 Router

Aggregates all v1 API routes under the /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.routes import (
    address,
    auth,
    cart,
    cart_items,
    category,
    media,
    order,
    payment,
    product,
    product_media,
    promo_code,
    shipping,
    stripe_webhook,
    upload,
    users,
    variants,
)

# Create the v1 router with prefix
router = APIRouter(prefix="/api/v1")

# Authentication
router.include_router(auth.router)

# Products
router.include_router(product.router)
router.include_router(product.admin_router)
router.include_router(variants.router)
router.include_router(variants.admin_router)

# Media
router.include_router(media.router)
router.include_router(media.admin_router)
router.include_router(product_media.router)
router.include_router(upload.admin_router)

# Categories
router.include_router(category.router)
router.include_router(category.admin_router)

# Shopping
router.include_router(cart.router)
router.include_router(cart_items.router)

# User management
router.include_router(address.router)
router.include_router(users.router)
router.include_router(users.admin_router)

# Orders & Payments
router.include_router(order.router)
router.include_router(order.admin_router)
router.include_router(payment.router)
router.include_router(stripe_webhook.router)

# Promo codes
router.include_router(promo_code.router)
router.include_router(promo_code.admin_router)

# Shipping
router.include_router(shipping.router)
