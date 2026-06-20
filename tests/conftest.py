import pytest


@pytest.fixture(autouse=True)
def spotify_env_vars(monkeypatch):
    """Injecte des variables d'environnement Spotify factices pour les tests."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/auth/callback")


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    """Base de données SQLite temporaire isolée par test."""
    p = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(p))
    return p
