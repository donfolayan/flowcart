from app.core import jwt as jwt_module
from app.core.jwt import create_access_token, create_refresh_token
from jose import jwt


def test_create_and_decode_access_token():
    data = {"sub": "user1"}
    token = create_access_token(data)
    assert isinstance(token, str)
    payload = jwt.decode(
        token, jwt_module.JWT_SECRET_KEY, algorithms=[jwt_module.JWT_ALGORITHM]
    )
    assert payload["sub"] == "user1"


def test_refresh_token_has_scope():
    data = {"sub": "user2"}
    token = create_refresh_token(data)
    payload = jwt.decode(
        token, jwt_module.JWT_SECRET_KEY, algorithms=[jwt_module.JWT_ALGORITHM]
    )
    assert payload.get("scope") == "refresh_token"
