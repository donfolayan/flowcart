import pytest
from uuid import uuid4
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi import Response, HTTPException

from app.api.v1.routes import cart_items as cart_routes
from app.schemas.cart_item import CartItemCreate, CartItemUpdate


def make_cart(**kwargs):
    """Helper to create a cart-like object."""
    defaults = {
        "id": uuid4(),
        "status": "active",
        "total": 0,
        "subtotal": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "version": 1,
        "items": [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_cart_item(**kwargs):
    """Helper to create a cart item-like object."""
    defaults = {
        "id": uuid4(),
        "cart_id": uuid4(),
        "product_id": uuid4(),
        "variant_id": None,
        "quantity": 1,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_add_item_to_cart_success():
    cart = make_cart()

    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.add_item_to_cart = AsyncMock(return_value=cart)
        mock_service_class.return_value = mock_service

        payload = CartItemCreate(product_id=uuid4(), variant_id=None, quantity=1)
        resp = Response()

        result = await cart_routes.add_item_to_cart(
            payload=payload,
            response=resp,
            db=AsyncMock(),
            user_id=None,
            session_id="test-session",
        )

        assert resp.headers.get("Location") == f"/cart/{cart.id}"
        assert result is not None


@pytest.mark.asyncio
async def test_add_item_to_cart_non_active_cart():
    cart = make_cart(status="archived")

    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.add_item_to_cart = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Cart is not active")
        )
        mock_service_class.return_value = mock_service

        payload = CartItemCreate(product_id=uuid4(), variant_id=None, quantity=1)
        resp = Response()

        with pytest.raises(HTTPException) as exc:
            await cart_routes.add_item_to_cart(
                payload=payload,
                response=resp,
                db=AsyncMock(),
                user_id=None,
                session_id="test-session",
            )
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_patch_cart_items_not_found():
    cart = make_cart()

    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.update_cart_item = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Cart item not found")
        )
        mock_service_class.return_value = mock_service

        payload = CartItemUpdate(quantity=2)

        with pytest.raises(HTTPException) as exc:
            await cart_routes.patch_cart_items(
                item_id=uuid4(),
                payload=payload,
                db=AsyncMock(),
                user_id=None,
                session_id="test-session",
            )
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_patch_cart_items_success():
    cart = make_cart()

    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.update_cart_item = AsyncMock(return_value=cart)
        mock_service_class.return_value = mock_service

        payload = CartItemUpdate(quantity=3)

        result = await cart_routes.patch_cart_items(
            item_id=uuid4(),
            payload=payload,
            db=AsyncMock(),
            user_id=None,
            session_id="test-session",
        )
        assert result is not None


@pytest.mark.asyncio
async def test_add_item_to_cart_integrity_error():
    cart = make_cart()

    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.add_item_to_cart = AsyncMock(
            side_effect=HTTPException(status_code=409, detail="Integrity error")
        )
        mock_service_class.return_value = mock_service

        payload = CartItemCreate(product_id=uuid4(), variant_id=None, quantity=1)
        resp = Response()

        with pytest.raises(HTTPException) as exc:
            await cart_routes.add_item_to_cart(
                payload=payload,
                response=resp,
                db=AsyncMock(),
                user_id=None,
                session_id="test-session",
            )
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_add_item_to_cart_reload_not_found():
    """Test case when cart reload fails."""
    cart = make_cart()

    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.add_item_to_cart = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Cart not found")
        )
        mock_service_class.return_value = mock_service

        payload = CartItemCreate(product_id=uuid4(), variant_id=None, quantity=1)
        resp = Response()

        with pytest.raises(HTTPException) as exc:
            await cart_routes.add_item_to_cart(
                payload=payload,
                response=resp,
                db=AsyncMock(),
                user_id=None,
                session_id="test-session",
            )
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_patch_cart_items_integrity_error():
    cart = make_cart()

    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.update_cart_item = AsyncMock(
            side_effect=HTTPException(status_code=409, detail="Integrity error")
        )
        mock_service_class.return_value = mock_service

        payload = CartItemUpdate(quantity=5)

        with pytest.raises(HTTPException) as exc:
            await cart_routes.patch_cart_items(
                item_id=uuid4(),
                payload=payload,
                db=AsyncMock(),
                user_id=None,
                session_id="test-session",
            )
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_cart_item_not_found_and_success():
    cart = make_cart()

    # Test not found case
    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.delete_cart_item = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Cart item not found")
        )
        mock_service_class.return_value = mock_service

        with pytest.raises(HTTPException) as exc:
            await cart_routes.delete_cart_item(
                item_id=uuid4(),
                db=AsyncMock(),
                user_id=None,
                session_id="test-session",
            )
        assert exc.value.status_code == 404

    # Test success case
    with (
        patch.object(
            cart_routes, "get_or_create_cart", new_callable=AsyncMock
        ) as mock_get_cart,
        patch.object(cart_routes, "CartService") as mock_service_class,
    ):
        mock_get_cart.return_value = cart
        mock_service = AsyncMock()
        mock_service.delete_cart_item = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        # Should not raise
        await cart_routes.delete_cart_item(
            item_id=uuid4(),
            db=AsyncMock(),
            user_id=None,
            session_id="test-session",
        )
