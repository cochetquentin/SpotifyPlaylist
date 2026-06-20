import pytest

from app.auth import tokens as tokens_module


@pytest.fixture()
def token_env(tmp_path, monkeypatch):
    """Redirige les tokens et la clé vers tmp_path via env var."""
    tokens_file = tmp_path / ".tokens.json"
    monkeypatch.setenv("SPOTIFY_TOKENS_FILE", str(tokens_file))
    return tokens_file


def test_save_and_load_tokens(token_env):
    data = {"access_token": "abc", "refresh_token": "xyz", "expires_at": 9999.0}
    tokens_module.save_tokens(data)
    assert tokens_module.load_tokens() == data
    assert token_env.exists()


@pytest.mark.skipif(
    __import__("sys").platform == "win32",
    reason="chmod 600 non applicable sur Windows (ACL différent)",
)
def test_tokens_file_permissions(token_env):
    tokens_module.save_tokens({"access_token": "secret"})
    mode = token_env.stat().st_mode & 0o777
    assert mode == 0o600


def test_load_tokens_returns_none_when_missing(token_env):
    assert tokens_module.load_tokens() is None


def test_clear_tokens_removes_files(token_env):
    tokens_module.save_tokens({"access_token": "abc"})
    assert token_env.exists()

    tokens_module.clear_tokens()

    assert not token_env.exists()
    assert not token_env.with_suffix(".key").exists()


def test_clear_tokens_noop_when_missing(token_env):
    tokens_module.clear_tokens()  # ne doit pas lever d'exception
