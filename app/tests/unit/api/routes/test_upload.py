import importlib


def test_api_upload_importable():
    mod = importlib.import_module("app.api.v1.routes.upload")
    assert mod is not None
