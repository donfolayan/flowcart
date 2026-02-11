import pytest
from fastapi import HTTPException

from app.core import errors


def test_http_error_raises_http_exception_with_errorresponse():
    with pytest.raises(HTTPException) as excinfo:
        errors.http_error(status_code=400, code="BAD_REQUEST", message="Bad request")

    exc = excinfo.value
    assert exc.status_code == 400
    assert isinstance(exc.detail, dict)
    assert exc.detail.get("code") == "BAD_REQUEST"
    assert exc.detail.get("message") == "Bad request"


def test_bad_request_helper_sets_defaults():
    with pytest.raises(HTTPException) as excinfo:
        errors.bad_request("BAD_REQUEST", "something is wrong")

    exc = excinfo.value
    assert exc.status_code == 400
    assert isinstance(exc.detail, dict)
    assert exc.detail.get("code") == "BAD_REQUEST"
    assert exc.detail.get("message") == "something is wrong"
