import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_SC_LOAD = "app.spotify_client.load_tokens"
_SC_SAVE = "app.spotify_client.save_tokens"
_SC_CLEAR = "app.spotify_client.clear_tokens"
_SC_HTTP = "app.spotify_client.httpx.AsyncClient"
_MAIN_HTTP = "app.main.httpx.AsyncClient"


def _async_client_mock(method: str, response: MagicMock) -> MagicMock:
    m = MagicMock()
    m.__aenter__ = AsyncMock(return_value=m)
    m.__aexit__ = AsyncMock(return_value=None)
    setattr(m, method, AsyncMock(return_value=response))
    return m


def test_me_unauthenticated():
    with patch(_SC_LOAD, return_value=None):
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
    with patch(_SC_LOAD, return_value=fake_tokens):
        with patch(_MAIN_HTTP, return_value=mock_client):
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
    with patch(_SC_LOAD, return_value=fake_tokens):
        with patch(_MAIN_HTTP, return_value=mock_client):
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

    mock_refresh = _async_client_mock("post", refresh_response)
    mock_me = _async_client_mock("get", me_response)

    with patch(_SC_LOAD, return_value=expired_tokens):
        with patch(_SC_SAVE):
            # httpx est un singleton : les deux modules partagent le même httpx.AsyncClient.
            # side_effect permet de router le premier appel (refresh) et le second (/me).
            with patch(_SC_HTTP, side_effect=[mock_refresh, mock_me]):
                resp = client.get("/me")

    assert resp.status_code == 200


def test_me_returns_502_when_refresh_fails_non_invalid_grant():
    """Un 400/401 sans invalid_grant → 502 (erreur serveur/config, pas session expirée)."""
    expired_tokens = {
        "access_token": "old_token",
        "refresh_token": "revoked_refresh",
        "expires_at": time.time() - 10,
    }
    refresh_response = MagicMock()
    refresh_response.status_code = 401
    refresh_response.json.return_value = {"error": "invalid_client"}
    refresh_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=refresh_response
    )

    mock_refresh = _async_client_mock("post", refresh_response)

    with patch(_SC_LOAD, return_value=expired_tokens):
        with patch(_SC_CLEAR) as mock_clear:
            with patch(_SC_HTTP, return_value=mock_refresh):
                resp = client.get("/me")

    assert resp.status_code == 502
    assert "Erreur Spotify" in resp.json()["detail"]
    mock_clear.assert_not_called()


def test_me_clears_tokens_on_invalid_grant():
    """Un refresh_token révoqué (invalid_grant) doit effacer les tokens locaux."""
    expired_tokens = {
        "access_token": "old_token",
        "refresh_token": "revoked_refresh",
        "expires_at": time.time() - 10,
    }
    refresh_response = MagicMock()
    refresh_response.status_code = 400
    refresh_response.json.return_value = {"error": "invalid_grant"}
    refresh_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request", request=MagicMock(), response=refresh_response
    )

    mock_refresh = _async_client_mock("post", refresh_response)

    with patch(_SC_LOAD, return_value=expired_tokens):
        with patch(_SC_CLEAR) as mock_clear:
            with patch(_SC_HTTP, return_value=mock_refresh):
                resp = client.get("/me")

    assert resp.status_code == 401
    assert "Session expirée" in resp.json()["detail"]
    mock_clear.assert_called_once()
