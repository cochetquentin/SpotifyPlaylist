from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.router import _pending_states
from app.main import app

client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def clear_pending_states():
    """Nettoie les états OAuth entre les tests."""
    _pending_states.clear()
    yield
    _pending_states.clear()


def test_login_redirects_to_spotify():
    resp = client.get("/auth/login")
    assert resp.status_code in (302, 307)
    assert "accounts.spotify.com/authorize" in resp.headers["location"]
    assert "test_client_id" in resp.headers["location"]
    assert "state=" in resp.headers["location"]


def test_login_adds_state_to_pending():
    client.get("/auth/login")
    assert len(_pending_states) == 1


def test_logout_clears_tokens():
    with patch("app.auth.router.clear_tokens") as mock_clear:
        resp = client.get("/auth/logout")
    assert resp.status_code == 200
    assert "Déconnecté" in resp.json()["message"]
    mock_clear.assert_called_once()


def test_callback_exchanges_code_and_saves_tokens():
    _pending_states.add("validstate123")

    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 3600,
    }

    mock_instance = MagicMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)
    mock_instance.post = AsyncMock(return_value=token_response)

    with patch("app.auth.router.httpx.AsyncClient", return_value=mock_instance):
        with patch("app.auth.router.save_tokens") as mock_save:
            resp = client.get("/auth/callback?code=spotify_code_123&state=validstate123")

    assert resp.status_code == 200
    assert "réussie" in resp.text
    mock_save.assert_called_once()
    saved = mock_save.call_args[0][0]
    assert saved["access_token"] == "new_access"
    assert "expires_at" in saved
    assert "validstate123" not in _pending_states


def test_callback_rejects_invalid_state():
    resp = client.get("/auth/callback?code=anycode&state=unknown_state")
    assert resp.status_code == 400
    assert "State OAuth invalide" in resp.json()["detail"]


def test_callback_returns_502_when_spotify_rejects_code():
    _pending_states.add("validstate456")

    token_response = MagicMock()
    token_response.status_code = 400
    token_response.text = "invalid_grant"

    mock_instance = MagicMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)
    mock_instance.post = AsyncMock(return_value=token_response)

    with patch("app.auth.router.httpx.AsyncClient", return_value=mock_instance):
        resp = client.get("/auth/callback?code=bad_code&state=validstate456")

    assert resp.status_code == 502
