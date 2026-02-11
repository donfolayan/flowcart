import importlib


def test_api_cart_items_importable():
    mod = importlib.import_module("app.api.v1.routes.cart_items")
    assert mod is not None
