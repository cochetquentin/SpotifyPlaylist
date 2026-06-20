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
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-public",
        "playlist-modify-private",
    ]
)

# États OAuth en attente de validation : state → timestamp d'émission
_pending_states: dict[str, float] = {}
_STATE_TTL = 300  # 5 minutes


def _prune_states() -> None:
    """Supprime les états OAuth expirés."""
    cutoff = time.time() - _STATE_TTL
    expired = [s for s, t in _pending_states.items() if t < cutoff]
    for s in expired:
        del _pending_states[s]


@router.get("/login", summary="Lancer le flux OAuth Spotify")
def login() -> RedirectResponse:
    _prune_states()
    state = secrets.token_urlsafe(32)
    _pending_states[state] = time.time()
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
async def callback(state: str, code: str | None = None, error: str | None = None) -> HTMLResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify a refusé l'autorisation : {error}")
    _prune_states()
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="State OAuth invalide ou expiré.")
    _pending_states.pop(state, None)

    if not code:
        raise HTTPException(status_code=400, detail="Paramètre 'code' manquant dans le callback.")

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
