import os
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.tokens import clear_tokens, save_tokens

router = APIRouter()

_AUTH_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"

_SCOPES = " ".join(
    [
        "user-read-private",
        "user-read-email",
        "user-library-read",
        "playlist-modify-public",
        "playlist-modify-private",
    ]
)

# États OAuth en attente de validation (single-user, en mémoire)
_pending_states: set[str] = set()


@router.get("/login", summary="Lancer le flux OAuth Spotify")
def login() -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    _pending_states.add(state)
    params = {
        "client_id": os.environ["SPOTIFY_CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": os.environ["SPOTIFY_REDIRECT_URI"],
        "scope": _SCOPES,
        "state": state,
        "show_dialog": "false",
    }
    return RedirectResponse(f"{_AUTH_URL}?{urlencode(params)}")


@router.get("/callback", summary="Callback OAuth — échange le code contre des tokens")
async def callback(code: str, state: str) -> HTMLResponse:
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="State OAuth invalide ou expiré.")
    _pending_states.discard(state)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": os.environ["SPOTIFY_REDIRECT_URI"],
            },
            auth=(os.environ["SPOTIFY_CLIENT_ID"], os.environ["SPOTIFY_CLIENT_SECRET"]),
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Spotify a rejeté le code : {resp.text}")

    tokens = resp.json()
    tokens["expires_at"] = time.time() + tokens["expires_in"]
    save_tokens(tokens)

    return HTMLResponse(
        content=(
            "<h2>Authentification réussie ✓</h2>"
            "<p>Vous pouvez fermer cette fenêtre et retourner dans le terminal.</p>"
        )
    )


@router.get("/logout", summary="Déconnexion — supprime les tokens locaux")
def logout() -> dict:
    clear_tokens()
    return {"message": "Déconnecté. Visitez /auth/login pour vous reconnecter."}
