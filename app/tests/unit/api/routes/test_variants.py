import importlib


def test_api_variants_importable():
    mod = importlib.import_module("app.api.v1.routes.variants")
    assert mod is not None
