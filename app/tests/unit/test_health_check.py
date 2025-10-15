from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"msg": "Application is running"}
