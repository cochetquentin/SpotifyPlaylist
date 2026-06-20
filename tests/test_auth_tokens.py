from unittest.mock import patch

import pytest

from app.auth import tokens as tokens_module


def test_save_and_load_tokens(tmp_path):
    tokens_file = tmp_path / ".tokens.json"
    data = {"access_token": "abc", "refresh_token": "xyz", "expires_at": 9999.0}

    with patch.object(tokens_module, "_TOKENS_PATH", tokens_file):
        tokens_module.save_tokens(data)
        loaded = tokens_module.load_tokens()

    assert loaded == data
    assert tokens_file.exists()


@pytest.mark.skipif(
    __import__("sys").platform == "win32",
    reason="chmod 600 non applicable sur Windows (ACL différent)",
)
def test_tokens_file_permissions(tmp_path):
    tokens_file = tmp_path / ".tokens.json"
    with patch.object(tokens_module, "_TOKENS_PATH", tokens_file):
        tokens_module.save_tokens({"access_token": "secret"})
    # chmod 600 : seul le propriétaire peut lire/écrire
    mode = tokens_file.stat().st_mode & 0o777
    assert mode == 0o600


def test_load_tokens_returns_none_when_missing(tmp_path):
    missing = tmp_path / ".tokens.json"
    with patch.object(tokens_module, "_TOKENS_PATH", missing):
        result = tokens_module.load_tokens()
    assert result is None


def test_clear_tokens_removes_file(tmp_path):
    tokens_file = tmp_path / ".tokens.json"
    tokens_file.write_text("{}")

    with patch.object(tokens_module, "_TOKENS_PATH", tokens_file):
        tokens_module.clear_tokens()

    assert not tokens_file.exists()


def test_clear_tokens_noop_when_missing(tmp_path):
    missing = tmp_path / ".tokens.json"
    with patch.object(tokens_module, "_TOKENS_PATH", missing):
        tokens_module.clear_tokens()  # ne doit pas lever d'exception
