def test_root_returns_status_json(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "Server is running"
    assert "Agricultural Science" in body["service"]


def test_health_returns_healthy_shape(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "openai_available" in body
    assert "d_id_configured" in body
