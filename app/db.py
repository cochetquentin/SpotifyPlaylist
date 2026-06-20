import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


def get_db_path() -> Path:
    return Path(os.environ.get("SQLITE_DB_PATH", "library.db"))


_CREATE_TRACKS = """
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    release_year INTEGER,
    duration_ms INTEGER,
    popularity INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_PLAYLISTS = """
CREATE TABLE IF NOT EXISTS playlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT,
    synced_at TIMESTAMP
);
"""

_CREATE_PLAYLIST_TRACKS = """
CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id TEXT,
    track_id TEXT,
    position INTEGER,
    PRIMARY KEY (playlist_id, track_id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);
"""

_CREATE_SYNCS = """
CREATE TABLE IF NOT EXISTS syncs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(db_path: Path | None = None) -> None:
    path = db_path or get_db_path()
    # sqlite3 context manager commits/rollbacks but does NOT close — close explicitly.
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            _CREATE_TRACKS + _CREATE_PLAYLISTS + _CREATE_PLAYLIST_TRACKS + _CREATE_SYNCS
        )
    finally:
        conn.close()


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_track(db_path: Path, track: dict) -> bool:
    """Insère un track. Retourne True si inséré, False si déjà présent (déduplication)."""
    release_date = track.get("album", {}).get("release_date", "") or ""
    release_year: int | None = int(release_date[:4]) if len(release_date) >= 4 else None
    artists = track.get("artists", [])
    artist = artists[0]["name"] if artists else ""

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO tracks
                (id, title, artist, album, release_year, duration_ms, popularity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                track["id"],
                track.get("name", ""),
                artist,
                track.get("album", {}).get("name"),
                release_year,
                track.get("duration_ms"),
                track.get("popularity"),
            ),
        )
    return cursor.rowcount > 0


def upsert_playlist(db_path: Path, playlist: dict) -> bool:
    """Insère ou met à jour une playlist. Retourne True si nouvelle ligne."""
    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM playlists WHERE id = ?", (playlist["id"],)
        ).fetchone()
        conn.execute(
            """
            INSERT INTO playlists (id, name, owner_id, synced_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                owner_id = excluded.owner_id,
                synced_at = CURRENT_TIMESTAMP
            """,
            (
                playlist["id"],
                playlist.get("name", ""),
                playlist.get("owner", {}).get("id"),
            ),
        )
    return existing is None


def upsert_playlist_track(db_path: Path, playlist_id: str, track_id: str, position: int) -> bool:
    """Associe un track à une playlist. Retourne True si nouvelle association.

    Met à jour la position si le track est déjà présent (réordonnancement de playlist).
    """
    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT playlist_id FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
            (playlist_id, track_id),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO playlist_tracks (playlist_id, track_id, position)
            VALUES (?, ?, ?)
            ON CONFLICT(playlist_id, track_id) DO UPDATE SET position = excluded.position
            """,
            (playlist_id, track_id, position),
        )
    return existing is None


def record_sync(db_path: Path | None = None) -> None:
    """Enregistre l'horodatage de la synchronisation courante."""
    path = db_path or get_db_path()
    with get_connection(path) as conn:
        conn.execute("INSERT INTO syncs (synced_at) VALUES (CURRENT_TIMESTAMP)")


def get_stats(db_path: Path | None = None) -> dict:
    path = db_path or get_db_path()
    with get_connection(path) as conn:
        track_count = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        playlist_count = conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
        last_sync = conn.execute("SELECT MAX(synced_at) FROM syncs").fetchone()[0]
    return {"tracks": track_count, "playlists": playlist_count, "last_sync": last_sync}
