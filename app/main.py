import os
import time

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.auth.router import router as auth_router
from app.auth.tokens import clear_tokens, load_tokens, save_tokens

load_dotenv()

app = FastAPI(
    title="SpotifyPlaylist",
    version="0.1.0",
    description="Tri automatique de musique Spotify en playlists thématiques par mood/contexte.",
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

_SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"
_TOKEN_URL = "https://accounts.spotify.com/api/token"


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/me", tags=["spotify"])
async def me() -> dict:
    """Retourne le profil Spotify de l'utilisateur authentifié."""
    tokens = load_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Non authentifié. Visitez /auth/login")

    if time.time() > tokens.get("expires_at", 0) - 60:
        tokens = await _refresh_tokens(tokens)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _SPOTIFY_ME_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Token invalide. Visitez /auth/login")
    resp.raise_for_status()
    return resp.json()


async def _refresh_tokens(tokens: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]},
            auth=(os.environ["SPOTIFY_CLIENT_ID"], os.environ["SPOTIFY_CLIENT_SECRET"]),
        )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (400, 401):
            try:
                error_code = exc.response.json().get("error", "")
            except Exception:
                error_code = ""
            if error_code == "invalid_grant":
                clear_tokens()
            raise HTTPException(
                status_code=401,
                detail="Session expirée. Visitez /auth/login pour vous reconnecter.",
            ) from exc
        raise
    new_tokens = resp.json()
    new_tokens["expires_at"] = time.time() + new_tokens["expires_in"]
    new_tokens.setdefault("refresh_token", tokens["refresh_token"])
    save_tokens(new_tokens)
    return new_tokens
