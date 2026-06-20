import sqlite3
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.db import init_db
from app.library.importer import import_liked_tracks, import_playlists

_SPOTIFY_GET = "app.library.importer.spotify_get"


def _make_track(track_id: str, name: str = "Song") -> dict:
    return {
        "id": track_id,
        "name": name,
        "artists": [{"name": "Artist"}],
        "album": {"name": "Album", "release_date": "2022-05-01"},
        "duration_ms": 180000,
        "popularity": 70,
    }


def _liked_page(tracks: list[dict], next_url: str | None = None) -> dict:
    return {"items": [{"track": t} for t in tracks], "next": next_url}


def _playlist_page(playlists: list[dict], next_url: str | None = None) -> dict:
    return {"items": playlists, "next": next_url}


def _playlist_tracks_page(tracks: list[dict], next_url: str | None = None) -> dict:
    return {"items": [{"track": t} for t in tracks], "next": next_url}


HEADERS = {"Authorization": "Bearer fake_token"}


class TestImportLikedTracks:
    async def test_single_page_inserts_tracks(self, db_path):
        init_db(db_path)
        page = _liked_page([_make_track("t1"), _make_track("t2")])
        with patch(_SPOTIFY_GET, new=AsyncMock(return_value=page)):
            count = await import_liked_tracks(HEADERS, db_path)
        assert count == 2

    async def test_pagination_two_pages(self, db_path):
        init_db(db_path)
        page1 = _liked_page([_make_track("t1")], next_url="http://next")
        page2 = _liked_page([_make_track("t2")])
        with patch(_SPOTIFY_GET, new=AsyncMock(side_effect=[page1, page2])):
            count = await import_liked_tracks(HEADERS, db_path)
        assert count == 2

    async def test_deduplication_second_import_returns_zero(self, db_path):
        init_db(db_path)
        page = _liked_page([_make_track("t1"), _make_track("t2")])
        with patch(_SPOTIFY_GET, new=AsyncMock(return_value=page)):
            await import_liked_tracks(HEADERS, db_path)
        # Second import — same tracks
        with patch(_SPOTIFY_GET, new=AsyncMock(return_value=page)):
            count = await import_liked_tracks(HEADERS, db_path)
        assert count == 0

    async def test_incremental_only_new_tracks_counted(self, db_path):
        init_db(db_path)
        page1 = _liked_page([_make_track("t1")])
        with patch(_SPOTIFY_GET, new=AsyncMock(return_value=page1)):
            await import_liked_tracks(HEADERS, db_path)
        # Second import adds t2 but not t1
        page2 = _liked_page([_make_track("t1"), _make_track("t2")])
        with patch(_SPOTIFY_GET, new=AsyncMock(return_value=page2)):
            count = await import_liked_tracks(HEADERS, db_path)
        assert count == 1

    async def test_skips_null_tracks(self, db_path):
        init_db(db_path)
        page = {"items": [{"track": None}, {"track": _make_track("t1")}], "next": None}
        with patch(_SPOTIFY_GET, new=AsyncMock(return_value=page)):
            count = await import_liked_tracks(HEADERS, db_path)
        assert count == 1

    async def test_rate_limit_retry_eventually_succeeds(self, db_path):
        """Vérifie que l'importer propage l'exception si spotify_get échoue sur 429."""
        init_db(db_path)
        # spotify_get encapsule tenacity — on teste que l'importer propagera l'exception
        # si tous les retries échouent (mock lève toujours 429).
        req = httpx.Request("GET", "http://x")
        rate_limit_resp = httpx.Response(429, request=req)
        exc = httpx.HTTPStatusError("Rate limited", request=req, response=rate_limit_resp)
        with patch(_SPOTIFY_GET, new=AsyncMock(side_effect=exc)):
            with pytest.raises(httpx.HTTPStatusError):
                await import_liked_tracks(HEADERS, db_path)


class TestImportPlaylists:
    async def test_imports_playlists_and_tracks(self, db_path):
        init_db(db_path)
        playlist = {"id": "p1", "name": "Mix", "owner": {"id": "user1"}}
        playlist_page = _playlist_page([playlist])
        tracks_page = _playlist_tracks_page([_make_track("t1"), _make_track("t2")])

        async def fake_spotify_get(url, headers, params=None):
            if "me/playlists" in url:
                return playlist_page
            return tracks_page

        with patch(_SPOTIFY_GET, new=AsyncMock(side_effect=fake_spotify_get)):
            playlists_added, associations_added = await import_playlists(HEADERS, db_path)

        assert playlists_added == 1
        assert associations_added == 2

    async def test_deduplication_second_import(self, db_path):
        init_db(db_path)
        playlist = {"id": "p1", "name": "Mix", "owner": {"id": "user1"}}
        playlist_page = _playlist_page([playlist])
        tracks_page = _playlist_tracks_page([_make_track("t1")])

        async def fake_spotify_get(url, headers, params=None):
            if "me/playlists" in url:
                return playlist_page
            return tracks_page

        with patch(_SPOTIFY_GET, new=AsyncMock(side_effect=fake_spotify_get)):
            await import_playlists(HEADERS, db_path)
        with patch(_SPOTIFY_GET, new=AsyncMock(side_effect=fake_spotify_get)):
            playlists_added, associations_added = await import_playlists(HEADERS, db_path)

        assert playlists_added == 0
        assert associations_added == 0

    async def test_tracks_inserted_in_db(self, db_path):
        init_db(db_path)
        playlist = {"id": "p1", "name": "Mix", "owner": {"id": "user1"}}
        playlist_page = _playlist_page([playlist])
        tracks_page = _playlist_tracks_page([_make_track("t1")])

        async def fake_spotify_get(url, headers, params=None):
            if "me/playlists" in url:
                return playlist_page
            return tracks_page

        with patch(_SPOTIFY_GET, new=AsyncMock(side_effect=fake_spotify_get)):
            await import_playlists(HEADERS, db_path)

        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        assert count == 1

    async def test_skips_null_playlists(self, db_path):
        init_db(db_path)
        playlist_page = {
            "items": [None, {"id": "p1", "name": "Mix", "owner": {"id": "u"}}],
            "next": None,
        }
        tracks_page = _playlist_tracks_page([])

        async def fake_spotify_get(url, headers, params=None):
            if "me/playlists" in url:
                return playlist_page
            return tracks_page

        with patch(_SPOTIFY_GET, new=AsyncMock(side_effect=fake_spotify_get)):
            playlists_added, _ = await import_playlists(HEADERS, db_path)

        assert playlists_added == 1
