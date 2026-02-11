import importlib


def test_api_address_importable():
    mod = importlib.import_module("app.api.v1.routes.address")
    assert mod is not None
