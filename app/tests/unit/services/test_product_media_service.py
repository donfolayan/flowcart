import importlib


def test_services_product_media_importable():
    mod = importlib.import_module("app.services.product_media")
    assert mod is not None
