from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    # Test root-level /api/health
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "Ministry of Tribal Affairs" in data["ministry"]

    # Test standardized /api/v1/health
    response_v1 = client.get("/api/v1/health")
    assert response_v1.status_code == 200
    data_v1 = response_v1.json()
    assert data_v1["status"] == "healthy"
    assert data_v1["database"] == "connected"


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Ministry of Tribal Affairs" in data["ministry"]
    assert "Phase 0" in data["phase"]
