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
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_get_product_by_id_not_found():
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.get = AsyncMock(side_effect=HTTPException(status_code=404, detail="Product not found"))
        mock_service_class.return_value = mock_service

        with pytest.raises(HTTPException) as exc:
            await product_routes.get_product_by_id(uuid4(), db=AsyncMock())
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_product_by_id_found():
    product = make_product()
    
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.get = AsyncMock(return_value=product)
        mock_service_class.return_value = mock_service

        res = await product_routes.get_product_by_id(product.id, db=AsyncMock())
        assert res.id == product.id


@pytest.mark.asyncio
async def test_list_all_products_returns_list():
    products = [make_product(name="Product 1"), make_product(name="Product 2")]
    
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.list = AsyncMock(return_value=products)
        mock_service_class.return_value = mock_service

        res = await product_routes.list_all_products(skip=0, limit=10, db=AsyncMock())
        assert isinstance(res, list)
        assert len(res) == 2
        assert res[0].id == products[0].id


@pytest.mark.asyncio
async def test_create_product_missing_base_price_raises():
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Base price is required")
        )
        mock_service_class.return_value = mock_service

        payload = ProductCreate.model_validate(
            {"name": "no-price", "slug": "no-price", "is_variable": False}
        )
        resp = Response()
        
        with pytest.raises(HTTPException) as exc:
            await product_routes.create_product(payload, resp, db=AsyncMock())
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_product_variable_active_without_variants_raises():
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Variants required")
        )
        mock_service_class.return_value = mock_service

        payload = ProductCreate.model_validate(
            {"name": "v", "slug": "v", "is_variable": True, "status": "active"}
        )
        resp = Response()
        
        with pytest.raises(HTTPException) as exc:
            await product_routes.create_product(payload, resp, db=AsyncMock())
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_product_not_found():
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.delete = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Product not found")
        )
        mock_service_class.return_value = mock_service

        with pytest.raises(HTTPException) as exc:
            await product_routes.delete_product(uuid4(), db=AsyncMock())
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_success():
    product_id = uuid4()
    
    with patch.object(product_routes, "ProductService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.delete = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        # Should not raise
        await product_routes.delete_product(product_id, db=AsyncMock())
        mock_service.delete.assert_called_once_with(product_id=product_id)
