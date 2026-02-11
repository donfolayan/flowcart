from app.schemas import shipping as shipping_schema_module
from app.schemas import payment as payment_schema_module
from app.util.sku import generate_unique_sku


def test_generate_unique_sku_format():
    sku = generate_unique_sku("widget")
    assert isinstance(sku, str)
    assert sku.count("-") == 1
    prefix, uid = sku.split("-")
    assert prefix.isupper()
    assert len(uid) == 5


def test_shipping_and_payment_schema_imports():
    # import modules and ensure classes exist
    assert hasattr(shipping_schema_module, "ShippingCreate") or hasattr(
        shipping_schema_module, "ShippingResponse"
    )
    assert hasattr(payment_schema_module, "PaymentCreate") or hasattr(
        payment_schema_module, "PaymentResponse"
    )
