import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate, UserLogin
from app.models.user import User


def test_password_validation():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", username="u1", password="short")


def test_login_requires_username_or_email():
    with pytest.raises(ValidationError):
        UserLogin(password="Somepass1!")


def test_model_metadata():
    # ensure table and columns exist in metadata
    tbl = User.__table__
    assert tbl.name == "users"
    cols = {c.name for c in tbl.columns}
    expected = {
        "id",
        "username",
        "email",
        "hashed_password",
        "is_active",
        "is_verified",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(cols)
