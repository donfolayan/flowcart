import importlib


def test_api_product_importable():
    mod = importlib.import_module("app.api.routes.product")
    assert mod is not None
