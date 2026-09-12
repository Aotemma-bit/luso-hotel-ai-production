from fastapi.testclient import TestClient

from app.main import app


def test_liveness_does_not_require_authentication():
    response = TestClient(app).get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_protected_endpoint_requires_authentication():
    response = TestClient(app).get("/api/dashboard/summary")
    assert response.status_code == 401
