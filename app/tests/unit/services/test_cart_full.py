def test_import_cart_service():
    import app.services.cart as cart

    assert hasattr(cart, "_add_item_to_cart") or hasattr(cart, "merge_guest_cart")
