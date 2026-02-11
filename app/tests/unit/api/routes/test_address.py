import importlib


def test_api_address_importable():
    mod = importlib.import_module("app.api.routes.address")
    assert mod is not None
