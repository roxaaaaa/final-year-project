import server as server_module


def test_cors_allow_origins_includes_loopback_for_localhost(monkeypatch):
    monkeypatch.setattr(server_module, "FRONTEND_URL", "http://localhost:3000")
    origins = server_module._cors_allow_origins()
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_cors_allow_origins_includes_localhost_for_loopback(monkeypatch):
    monkeypatch.setattr(server_module, "FRONTEND_URL", "http://127.0.0.1:3000")
    origins = server_module._cors_allow_origins()
    assert "http://127.0.0.1:3000" in origins
    assert "http://localhost:3000" in origins
