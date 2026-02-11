import importlib


def test_api_order_importable():
    mod = importlib.import_module("app.api.routes.order")
    assert mod is not None
