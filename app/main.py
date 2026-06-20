import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.auth.router import router as auth_router
from app.library.router import router as library_router
from app.spotify_client import get_valid_tokens

load_dotenv()

app = FastAPI(
    title="SpotifyPlaylist",
    version="0.2.0",
    description="Tri automatique de musique Spotify en playlists thématiques par mood/contexte.",
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(library_router)

_SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/me", tags=["spotify"])
async def me() -> dict:
    """Retourne le profil Spotify de l'utilisateur authentifié."""
    tokens = await get_valid_tokens()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _SPOTIFY_ME_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Token invalide. Visitez /auth/login")
    resp.raise_for_status()
    return resp.json()
