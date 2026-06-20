import time
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_SC_LOAD = "app.spotify_client.load_tokens"
_IMPORT_LIKED = "app.library.router.import_liked_tracks"
_IMPORT_PLAYLISTS = "app.library.router.import_playlists"
_INIT_DB = "app.library.router.init_db"
_RECORD_SYNC = "app.library.router.record_sync"


def _valid_tokens() -> dict:
    return {
        "access_token": "fake_token",
        "refresh_token": "fake_refresh",
        "expires_at": time.time() + 3600,
    }


class TestTriggerImport:
    def test_import_returns_401_when_unauthenticated(self):
        with patch(_SC_LOAD, return_value=None):
            resp = client.post("/import")
        assert resp.status_code == 401

    def test_import_returns_stats_on_success(self, db_path):
        # import_playlists retourne maintenant (playlists, associations, nouveaux_tracks)
        with patch(_SC_LOAD, return_value=_valid_tokens()):
            with patch(_INIT_DB):
                with patch(_RECORD_SYNC):
                    with patch(_IMPORT_LIKED, new=AsyncMock(return_value=42)):
                        with patch(_IMPORT_PLAYLISTS, new=AsyncMock(return_value=(5, 120, 3))):
                            resp = client.post("/import")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tracks_added"] == 45  # 42 liked + 3 playlist-only
        assert data["playlists_added"] == 5
        assert data["playlist_tracks_added"] == 120

    def test_import_incremental_returns_zeros(self, db_path):
        with patch(_SC_LOAD, return_value=_valid_tokens()):
            with patch(_INIT_DB):
                with patch(_RECORD_SYNC):
                    with patch(_IMPORT_LIKED, new=AsyncMock(return_value=0)):
                        with patch(_IMPORT_PLAYLISTS, new=AsyncMock(return_value=(0, 0, 0))):
                            resp = client.post("/import")

        assert resp.status_code == 200
        assert resp.json() == {"tracks_added": 0, "playlists_added": 0, "playlist_tracks_added": 0}


class TestLibraryStats:
    def test_stats_without_db_returns_zeros(self, db_path):
        # db_path exists in env but file doesn't exist yet
        resp = client.get("/library/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"tracks": 0, "playlists": 0, "last_sync": None}

    def test_stats_after_import(self, db_path):
        from app.db import init_db, record_sync, upsert_playlist, upsert_track

        init_db(db_path)
        upsert_track(
            db_path,
            {
                "id": "t1",
                "name": "Song",
                "type": "track",
                "artists": [{"name": "Artist"}],
                "album": {"name": "Album", "release_date": "2022-01-01"},
                "duration_ms": 200000,
                "popularity": 60,
            },
        )
        upsert_playlist(db_path, {"id": "p1", "name": "Mix", "owner": {"id": "u"}})
        record_sync(db_path)  # last_sync vient de la table syncs, pas de imported_at

        resp = client.get("/library/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tracks"] == 1
        assert data["playlists"] == 1
        assert data["last_sync"] is not None
