import pytest


@pytest.fixture(autouse=True)
def spotify_env_vars(monkeypatch):
    """Injecte des variables d'environnement Spotify factices pour les tests."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/auth/callback")
