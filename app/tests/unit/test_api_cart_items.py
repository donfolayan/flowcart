import importlib


def test_api_cart_items_importable():
    mod = importlib.import_module("app.api.routes.cart_items")
    assert mod is not None
