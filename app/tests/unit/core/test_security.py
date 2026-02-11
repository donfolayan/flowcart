from app.core.security import hash_password, verify_password


def test_hash_and_verify():
    pw = "Str0ng!Pass"
    h = hash_password(pw)
    assert isinstance(h, str)
    assert verify_password(pw, h) is True
    assert verify_password("wrong", h) is False


def test_long_password():
    pw = "a" * 200
    h = hash_password(pw)
    assert verify_password(pw, h) is True
