from fastapi.testclient import TestClient


def test_list_active_schemes(client: TestClient):
    response = client.get("/api/v1/schemes/")
    assert response.status_code == 200
    schemes = response.json()
    assert len(schemes) >= 2

    codes = [s["scheme_code"] for s in schemes]
    assert "NFST" in codes
    assert "NOS" in codes

    for s in schemes:
        # Verify Phase 0 scheme foundation fields
        assert "scheme_version" in s
        assert s["scheme_version"] == "1.0"
        assert s["is_demo"] is True
        assert "DEMO" in s["description"] or "PROTOTYPE" in s["description"]


def test_get_scheme_by_id(client: TestClient):
    # Fetch all first
    list_res = client.get("/api/v1/schemes/")
    assert list_res.status_code == 200
    schemes = list_res.json()
    first_scheme = schemes[0]

    # Fetch by ID
    res = client.get(f"/api/v1/schemes/{first_scheme['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == first_scheme["id"]
    assert data["scheme_code"] == first_scheme["scheme_code"]
