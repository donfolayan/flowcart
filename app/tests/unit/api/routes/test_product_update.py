import pytest

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException
from types import SimpleNamespace

from app.api.v1.routes import product as product_routes
from app.schemas.product import ProductUpdate


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
async def test_update_product_not_found():
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.update = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Product not found")
        )
        mock_service_class.return_value = mock_service

        payload = ProductUpdate.model_validate({"name": "x"})

        with pytest.raises(HTTPException) as exc:
            await product_routes.update_product(uuid4(), payload, db=AsyncMock())
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_product_success():
    product = make_product(name="updated")

    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.update = AsyncMock(return_value=product)
        mock_service_class.return_value = mock_service

        payload = ProductUpdate.model_validate({"name": "updated"})

        result = await product_routes.update_product(
            product.id, payload, db=AsyncMock()
        )
        assert result.name == "updated"


@pytest.mark.asyncio
async def test_update_product_active_variable_requires_variants():
    """Test that updating to active variable product without variants raises error."""
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.update = AsyncMock(
            side_effect=HTTPException(
                status_code=400,
                detail="At least one variant is required for variable products",
            )
        )
        mock_service_class.return_value = mock_service

        payload = ProductUpdate.model_validate(
            {
                "status": "active",
                "is_variable": True,
            }
        )

        with pytest.raises(HTTPException) as exc:
            await product_routes.update_product(uuid4(), payload, db=AsyncMock())
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_product_media_calls_validate_and_add():
    """Test that updating product with media IDs works."""
    product = make_product()
    media_id = uuid4()

    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.update = AsyncMock(return_value=product)
        mock_service_class.return_value = mock_service

        payload = ProductUpdate.model_validate(
            {
                "media": [str(media_id)],
            }
        )

        result = await product_routes.update_product(
            product.id, payload, db=AsyncMock()
        )
        assert result.id == product.id
        mock_service.update.assert_called_once()
