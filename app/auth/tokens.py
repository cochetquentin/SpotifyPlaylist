import json
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet


def _tokens_path() -> Path:
    """Résolu à l'appel pour respecter load_dotenv() et les surcharges de tests."""
    return Path(os.environ.get("SPOTIFY_TOKENS_FILE", ".tokens.json"))


def _key_path() -> Path:
    return _tokens_path().with_suffix(".key")


def _get_fernet() -> Fernet:
    kp = _key_path()
    if not kp.exists():
        key = Fernet.generate_key()
        kp.write_bytes(key)
        kp.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return Fernet(kp.read_bytes())


def save_tokens(tokens: dict) -> None:
    """Chiffre (Fernet) et sauvegarde les tokens (chmod 600)."""
    encrypted = _get_fernet().encrypt(json.dumps(tokens).encode())
    tp = _tokens_path()
    tp.write_bytes(encrypted)
    tp.chmod(stat.S_IRUSR | stat.S_IWUSR)


def load_tokens() -> dict | None:
    """Déchiffre et charge les tokens. Retourne None si absent."""
    tp = _tokens_path()
    if not tp.exists():
        return None
    return json.loads(_get_fernet().decrypt(tp.read_bytes()).decode())


def clear_tokens() -> None:
    """Supprime tokens et clé (déconnexion complète)."""
    for p in (_tokens_path(), _key_path()):
        if p.exists():
            p.unlink()
