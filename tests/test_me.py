import time
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# main.py importe load_tokens/save_tokens directement → on patche dans app.main
_LOAD = "app.main.load_tokens"
_SAVE = "app.main.save_tokens"


def _async_client_mock(method: str, response: MagicMock) -> MagicMock:
    """Crée un mock httpx.AsyncClient pour un seul appel GET ou POST."""
    m = MagicMock()
    m.__aenter__ = AsyncMock(return_value=m)
    m.__aexit__ = AsyncMock(return_value=None)
    setattr(m, method, AsyncMock(return_value=response))
    return m


def test_me_unauthenticated():
    with patch(_LOAD, return_value=None):
        resp = client.get("/me")
    assert resp.status_code == 401
    assert "Non authentifié" in resp.json()["detail"]


def test_me_returns_spotify_profile():
    fake_tokens = {
        "access_token": "fake_token",
        "refresh_token": "fake_refresh",
        "expires_at": time.time() + 3600,
    }
    me_response = MagicMock()
    me_response.status_code = 200
    me_response.json.return_value = {"id": "user123", "display_name": "Test User"}
    me_response.raise_for_status.return_value = None

    mock_client = _async_client_mock("get", me_response)
    with patch(_LOAD, return_value=fake_tokens):
        with patch("app.main.httpx.AsyncClient", return_value=mock_client):
            resp = client.get("/me")

    assert resp.status_code == 200
    assert resp.json()["id"] == "user123"


def test_me_returns_401_when_spotify_rejects_token():
    fake_tokens = {
        "access_token": "bad_token",
        "refresh_token": "refresh",
        "expires_at": time.time() + 3600,
    }
    me_response = MagicMock()
    me_response.status_code = 401

    mock_client = _async_client_mock("get", me_response)
    with patch(_LOAD, return_value=fake_tokens):
        with patch("app.main.httpx.AsyncClient", return_value=mock_client):
            resp = client.get("/me")

    assert resp.status_code == 401
    assert "Token invalide" in resp.json()["detail"]


def test_me_triggers_refresh_when_token_expired():
    expired_tokens = {
        "access_token": "old_token",
        "refresh_token": "refresh_tok",
        "expires_at": time.time() - 10,
    }
    refresh_response = MagicMock()
    refresh_response.status_code = 200
    refresh_response.json.return_value = {"access_token": "new_token", "expires_in": 3600}
    refresh_response.raise_for_status.return_value = None

    me_response = MagicMock()
    me_response.status_code = 200
    me_response.json.return_value = {"id": "user123"}
    me_response.raise_for_status.return_value = None

    # _refresh_tokens ouvre un AsyncClient (POST), puis /me en ouvre un second (GET)
    mock_refresh = _async_client_mock("post", refresh_response)
    mock_me = _async_client_mock("get", me_response)

    with patch(_LOAD, return_value=expired_tokens):
        with patch(_SAVE):
            with patch("app.main.httpx.AsyncClient", side_effect=[mock_refresh, mock_me]):
                resp = client.get("/me")

    assert resp.status_code == 200
