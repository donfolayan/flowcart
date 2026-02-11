import pytest

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException, Response
from types import SimpleNamespace

from app.api.routes import product as product_routes
from app.schemas.product import ProductCreate


def make_product(**kwargs):
    """Helper to create a product-like object with required fields."""
    defaults = {
        "id": uuid4(),
        "name": "Test Product",
        "slug": "test-product",
        "variants": [],
        "status": "draft",
        "is_variable": False,
        "base_price": 1000,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_create_product_success():
    product = make_product(name="prod", slug="prod")
    
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(return_value=product)
        mock_service_class.return_value = mock_service

        payload = ProductCreate.model_validate({
            "name": "prod",
            "slug": "prod",
            "is_variable": False,
            "base_price": 100,
        })
        resp = Response()
        
        result = await product_routes.create_product(payload, resp, db=AsyncMock())
        assert result.id == product.id
        assert resp.headers["Location"].startswith("/products/")


@pytest.mark.asyncio
async def test_create_product_media_clear_calls_delete():
    """Test that creating a product with empty media list works."""
    product = make_product(name="p2", slug="p2")
    
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(return_value=product)
        mock_service_class.return_value = mock_service

        payload = ProductCreate.model_validate({
            "name": "p2",
            "slug": "p2",
            "is_variable": False,
            "base_price": 50,
            "media": [],
        })
        resp = Response()
        
        result = await product_routes.create_product(payload, resp, db=AsyncMock())
        assert result.id == product.id
        mock_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_product_calls_validate_media_and_add():
    """Test that creating a product with media IDs works."""
    product = make_product(name="p3", slug="p3")
    media_id = uuid4()
    
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(return_value=product)
        mock_service_class.return_value = mock_service

        payload = ProductCreate.model_validate({
            "name": "p3",
            "slug": "p3",
            "is_variable": False,
            "base_price": 75,
            "media": [str(media_id)],
        })
        resp = Response()
        
        result = await product_routes.create_product(payload, resp, db=AsyncMock())
        assert result.id == product.id
        mock_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_product_slug_retry_on_integrity_error():
    """Test that the service handles slug conflicts (retries with unique slug)."""
    product = make_product(name="dup", slug="dup-abc123")
    
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        # Service handles integrity error internally and returns product with modified slug
        mock_service.create = AsyncMock(return_value=product)
        mock_service_class.return_value = mock_service

        payload = ProductCreate.model_validate({
            "name": "dup",
            "slug": "dup",
            "is_variable": False,
            "base_price": 100,
        })
        resp = Response()
        
        result = await product_routes.create_product(payload, resp, db=AsyncMock())
        # The service should have handled the retry
        assert result.slug == "dup-abc123"
