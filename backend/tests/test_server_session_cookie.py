import server as server_module


def test_session_cookie_https_only_false_by_default(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    assert server_module._session_cookie_https_only() is False


def test_session_cookie_https_only_true_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    assert server_module._session_cookie_https_only() is True


def test_session_cookie_https_only_explicit_overrides_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "0")
    assert server_module._session_cookie_https_only() is False
