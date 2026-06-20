from fastapi import APIRouter

from app.db import get_db_path, get_stats, init_db
from app.library.importer import import_liked_tracks, import_playlists
from app.spotify_client import get_valid_tokens

router = APIRouter()


@router.post("/import", tags=["library"])
async def trigger_import() -> dict:
    """Déclenche l'import complet : liked songs + playlists. Mode incrémental automatique."""
    tokens = await get_valid_tokens()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    db_path = get_db_path()
    init_db(db_path)

    tracks_added = await import_liked_tracks(headers, db_path)
    playlists_added, playlist_tracks_added = await import_playlists(headers, db_path)

    return {
        "tracks_added": tracks_added,
        "playlists_added": playlists_added,
        "playlist_tracks_added": playlist_tracks_added,
    }


@router.get("/library/stats", tags=["library"])
def library_stats() -> dict:
    """Retourne les statistiques de la bibliothèque importée."""
    db_path = get_db_path()
    if not db_path.exists():
        return {"tracks": 0, "playlists": 0, "last_sync": None}
    return get_stats(db_path)
