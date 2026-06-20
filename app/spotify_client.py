import os
import time

import httpx
from fastapi import HTTPException
from tenacity import retry, retry_if_exception, stop_after_attempt

from app.auth.tokens import clear_tokens, load_tokens, save_tokens

_TOKEN_URL = "https://accounts.spotify.com/api/token"


def _is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


async def _refresh_tokens(tokens: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
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
            hint = error_code or str(exc.response.status_code)
            raise HTTPException(
                status_code=502,
                detail=f"Erreur Spotify lors du renouvellement du token : {hint}",
            ) from exc
        raise
    new_tokens = resp.json()
    new_tokens["expires_at"] = time.time() + new_tokens["expires_in"]
    new_tokens.setdefault("refresh_token", tokens["refresh_token"])
    save_tokens(new_tokens)
    return new_tokens


async def get_valid_tokens() -> dict:
    """Charge les tokens et les rafraîchit si nécessaire. Lève 401 si absent."""
    tokens = load_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Non authentifié. Visitez /auth/login")
    if time.time() > tokens.get("expires_at", 0) - 60:
        tokens = await _refresh_tokens(tokens)
    return tokens


def _retry_after_wait(retry_state) -> float:
    """Respecte le header Retry-After de Spotify ; défaut 1s."""
    exc = retry_state.outcome.exception()
    if isinstance(exc, httpx.HTTPStatusError):
        header = exc.response.headers.get("Retry-After", "")
        try:
            return max(1.0, float(header))
        except (ValueError, TypeError):
            pass
    return 1.0


@retry(
    retry=retry_if_exception(_is_rate_limited),
    wait=_retry_after_wait,
    stop=stop_after_attempt(5),
    reraise=True,
)
async def spotify_get(url: str, headers: dict, params: dict | None = None) -> dict:
    """GET Spotify API avec retry automatique sur rate limit (429)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
    if resp.status_code == 429:
        raise httpx.HTTPStatusError("Rate limited", request=resp.request, response=resp)
    resp.raise_for_status()
    return resp.json()
