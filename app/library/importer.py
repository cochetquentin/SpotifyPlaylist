from pathlib import Path

import httpx

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


async def import_playlists(headers: dict, db_path: Path) -> tuple[int, int, int]:
    """Pagine /v1/me/playlists puis les tracks de chaque playlist.

    Retourne (playlists_insérées, associations_insérées, nouveaux_tracks_via_playlist).
    Les playlists inaccessibles (403) sont ignorées silencieusement.
    """
    url: str | None = _PLAYLISTS_URL
    playlists_inserted = 0
    associations_inserted = 0
    new_tracks_via_playlist = 0

    while url:
        data = await spotify_get(url, headers, {"limit": 50})
        for playlist in data.get("items", []):
            if not playlist or not playlist.get("id"):
                continue
            if upsert_playlist(db_path, playlist):
                playlists_inserted += 1
            try:
                assoc, new_tracks = await _import_playlist_tracks(headers, db_path, playlist["id"])
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    continue  # Playlist inaccessible — skip, pas d'abort global
                raise
            associations_inserted += assoc
            new_tracks_via_playlist += new_tracks
        url = data.get("next")

    return playlists_inserted, associations_inserted, new_tracks_via_playlist


async def _import_playlist_tracks(
    headers: dict, db_path: Path, playlist_id: str
) -> tuple[int, int]:
    """Pagine GET /v1/playlists/{id}/tracks (100 par page).

    Retourne (associations_insérées, nouveaux_tracks_insérés).
    Les épisodes de podcast (type != "track") sont ignorés.
    """
    url: str | None = _PLAYLIST_TRACKS_URL.format(playlist_id=playlist_id)
    inserted = 0
    new_tracks = 0
    position = 0

    while url:
        data = await spotify_get(url, headers, {"limit": 100})
        for item in data.get("items", []):
            track = item.get("track")
            if not track or not track.get("id") or track.get("type") != "track":
                position += 1
                continue
            # S'assurer que le track existe en DB (peut ne pas être dans les liked songs)
            if upsert_track(db_path, track):
                new_tracks += 1
            if upsert_playlist_track(db_path, playlist_id, track["id"], position):
                inserted += 1
            position += 1
        url = data.get("next")

    return inserted, new_tracks
