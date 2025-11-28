import importlib


def test_services_cart_importable():
    mod = importlib.import_module("app.services.cart")
    assert mod is not None
