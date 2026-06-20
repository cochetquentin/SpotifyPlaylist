from pathlib import Path

from app.db import upsert_playlist, upsert_playlist_track, upsert_track
from app.spotify_client import spotify_get

_LIKED_TRACKS_URL = "https://api.spotify.com/v1/me/tracks"
_PLAYLISTS_URL = "https://api.spotify.com/v1/me/playlists"
_PLAYLIST_TRACKS_URL = "https://api.spotify.com/v1/playlists/{playlist_id}/tracks"


async def import_liked_tracks(headers: dict, db_path: Path) -> int:
    """Pagine GET /v1/me/tracks (50 par page) et insère les nouveaux tracks.

    Retourne le nombre de tracks effectivement insérés (0 si déjà présents).
    """
    url: str | None = _LIKED_TRACKS_URL
    inserted = 0
    while url:
        data = await spotify_get(url, headers, {"limit": 50})
        for item in data.get("items", []):
            track = item.get("track")
            if track and track.get("id"):
                if upsert_track(db_path, track):
                    inserted += 1
        url = data.get("next")
    return inserted


async def import_playlists(headers: dict, db_path: Path) -> tuple[int, int]:
    """Pagine /v1/me/playlists puis les tracks de chaque playlist.

    Retourne (playlists_insérées, associations_playlist_track_insérées).
    """
    url: str | None = _PLAYLISTS_URL
    playlists_inserted = 0
    associations_inserted = 0

    while url:
        data = await spotify_get(url, headers, {"limit": 50})
        for playlist in data.get("items", []):
            if not playlist or not playlist.get("id"):
                continue
            if upsert_playlist(db_path, playlist):
                playlists_inserted += 1
            assoc = await _import_playlist_tracks(headers, db_path, playlist["id"])
            associations_inserted += assoc
        url = data.get("next")

    return playlists_inserted, associations_inserted


async def _import_playlist_tracks(headers: dict, db_path: Path, playlist_id: str) -> int:
    """Pagine GET /v1/playlists/{id}/tracks (100 par page) et insère les associations."""
    url: str | None = _PLAYLIST_TRACKS_URL.format(playlist_id=playlist_id)
    inserted = 0
    position = 0

    while url:
        data = await spotify_get(url, headers, {"limit": 100})
        for item in data.get("items", []):
            track = item.get("track")
            if not track or not track.get("id"):
                position += 1
                continue
            # S'assurer que le track existe en DB (peut ne pas être dans les liked songs)
            upsert_track(db_path, track)
            if upsert_playlist_track(db_path, playlist_id, track["id"], position):
                inserted += 1
            position += 1
        url = data.get("next")

    return inserted
