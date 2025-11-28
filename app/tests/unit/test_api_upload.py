import importlib


def test_api_upload_importable():
    mod = importlib.import_module("app.api.routes.upload")
    assert mod is not None
