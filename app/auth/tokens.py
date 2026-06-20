import json
import os
import stat
from pathlib import Path

_TOKENS_PATH = Path(os.environ.get("SPOTIFY_TOKENS_FILE", ".tokens.json"))


def save_tokens(tokens: dict) -> None:
    """Sauvegarde les tokens dans un fichier local (chmod 600)."""
    _TOKENS_PATH.write_text(json.dumps(tokens, indent=2))
    _TOKENS_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)


def load_tokens() -> dict | None:
    """Charge les tokens depuis le fichier local. Retourne None si absent."""
    if not _TOKENS_PATH.exists():
        return None
    return json.loads(_TOKENS_PATH.read_text())


def clear_tokens() -> None:
    """Supprime le fichier de tokens (déconnexion)."""
    if _TOKENS_PATH.exists():
        _TOKENS_PATH.unlink()
