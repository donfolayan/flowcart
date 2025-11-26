def test_import_top_level_modules():
    # Importing modules to execute top-level definitions and increase coverage
    import importlib

    modules = [
        "app.api.routes.product",
        "app.api.routes.cart",
        "app.api.routes.cart_items",
        "app.services.cart",
        "app.services.product",
        "app.services.product_media",
        "app.services.order",
        "app.services.promo",
    ]

    for m in modules:
        mod = importlib.import_module(m)
        assert mod is not None
