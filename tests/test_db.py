import sqlite3

import pytest

from app.db import (
    get_stats,
    init_db,
    record_sync,
    upsert_playlist,
    upsert_playlist_track,
    upsert_track,
)


def _make_track(track_id: str = "t1", popularity: int = 80) -> dict:
    return {
        "id": track_id,
        "name": "Song Title",
        "artists": [{"name": "Artist Name"}],
        "album": {"name": "Album Name", "release_date": "2023-01-01"},
        "duration_ms": 210000,
        "popularity": popularity,
    }


def _make_playlist(playlist_id: str = "p1") -> dict:
    return {
        "id": playlist_id,
        "name": "My Playlist",
        "owner": {"id": "user123"},
    }


class TestInitDb:
    def test_creates_all_tables(self, db_path):
        init_db(db_path)
        with sqlite3.connect(db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert {"tracks", "playlists", "playlist_tracks", "syncs"}.issubset(tables)

    def test_idempotent(self, db_path):
        init_db(db_path)
        init_db(db_path)  # doit pas lever d'exception


class TestUpsertTrack:
    def test_inserts_new_track(self, db_path):
        init_db(db_path)
        result = upsert_track(db_path, _make_track("t1"))
        assert result is True

    def test_deduplication_returns_false_on_second_insert(self, db_path):
        init_db(db_path)
        upsert_track(db_path, _make_track("t1"))
        result = upsert_track(db_path, _make_track("t1"))
        assert result is False

    def test_track_data_stored_correctly(self, db_path):
        init_db(db_path)
        upsert_track(db_path, _make_track("t1"))
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT * FROM tracks WHERE id='t1'").fetchone()
        assert row is not None
        assert row[1] == "Song Title"  # title
        assert row[2] == "Artist Name"  # artist
        assert row[4] == 2023  # release_year

    def test_missing_release_date_stores_none(self, db_path):
        init_db(db_path)
        track = _make_track("t2")
        track["album"]["release_date"] = ""
        upsert_track(db_path, track)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT release_year FROM tracks WHERE id='t2'").fetchone()
        assert row[0] is None

    def test_multiple_different_tracks(self, db_path):
        init_db(db_path)
        upsert_track(db_path, _make_track("t1"))
        upsert_track(db_path, _make_track("t2"))
        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        assert count == 2


class TestUpsertPlaylist:
    def test_inserts_new_playlist(self, db_path):
        init_db(db_path)
        result = upsert_playlist(db_path, _make_playlist("p1"))
        assert result is True

    def test_deduplication_returns_false(self, db_path):
        init_db(db_path)
        upsert_playlist(db_path, _make_playlist("p1"))
        result = upsert_playlist(db_path, _make_playlist("p1"))
        assert result is False


class TestUpsertPlaylistTrack:
    def test_inserts_association(self, db_path):
        init_db(db_path)
        upsert_track(db_path, _make_track("t1"))
        upsert_playlist(db_path, _make_playlist("p1"))
        result = upsert_playlist_track(db_path, "p1", "t1", 0)
        assert result is True

    def test_deduplication_returns_false(self, db_path):
        init_db(db_path)
        upsert_track(db_path, _make_track("t1"))
        upsert_playlist(db_path, _make_playlist("p1"))
        upsert_playlist_track(db_path, "p1", "t1", 0)
        result = upsert_playlist_track(db_path, "p1", "t1", 0)
        assert result is False


class TestGetStats:
    def test_empty_db_returns_zeros(self, db_path):
        init_db(db_path)
        stats = get_stats(db_path)
        assert stats["tracks"] == 0
        assert stats["playlists"] == 0
        assert stats["last_sync"] is None

    def test_returns_correct_counts(self, db_path):
        init_db(db_path)
        upsert_track(db_path, _make_track("t1"))
        upsert_track(db_path, _make_track("t2"))
        upsert_playlist(db_path, _make_playlist("p1"))
        stats = get_stats(db_path)
        assert stats["tracks"] == 2
        assert stats["playlists"] == 1
        assert stats["last_sync"] is None  # pas encore de sync enregistrée

    def test_record_sync_sets_last_sync(self, db_path):
        init_db(db_path)
        assert get_stats(db_path)["last_sync"] is None
        record_sync(db_path)
        assert get_stats(db_path)["last_sync"] is not None

    def test_record_sync_updates_even_without_new_tracks(self, db_path):
        """last_sync reflète le dernier import même si aucun nouveau track n'a été inséré."""
        init_db(db_path)
        record_sync(db_path)
        first = get_stats(db_path)["last_sync"]
        assert first is not None
        record_sync(db_path)
        second = get_stats(db_path)["last_sync"]
        assert second >= first

    @pytest.mark.parametrize("track_id", ["abc", "xyz"])
    def test_parametrize_counts(self, db_path, track_id):
        init_db(db_path)
        upsert_track(db_path, _make_track(track_id))
        stats = get_stats(db_path)
        assert stats["tracks"] == 1
