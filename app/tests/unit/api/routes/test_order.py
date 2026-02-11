import importlib


def test_api_order_importable():
    mod = importlib.import_module("app.api.v1.routes.order")
    assert mod is not None
