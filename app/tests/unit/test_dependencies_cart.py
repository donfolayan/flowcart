import importlib


def test_dependencies_cart_importable():
    mod = importlib.import_module("app.api.dependencies.cart")
    assert mod is not None
