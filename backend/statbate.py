"""Cliente de Statbate Plus: inicio de sesión (OAuth 2.0 con PKCE) y consultas.

Contrato: https://docs.statbate.com/docs/plus/integrations/sign-in-with-statbate/
"""

import base64
import hashlib
import re
import secrets
from urllib.parse import urlencode

import httpx

from .config import Config

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class SignInRequired(Exception):
    """El acceso ya no vale: hay que volver a iniciar sesión."""


class PlanRequired(Exception):
    """El plan de la cuenta no cubre esta consulta."""


class RateLimited(Exception):
    pass


def clean_username(text):
    """Acepta un nombre o un enlace a su sala y devuelve el nombre, o None."""
    text = (text or "").strip().split("?")[0].rstrip("/")
    if "/" in text:
        text = text.rsplit("/", 1)[1]
    text = text.lstrip("@")
    return text if USERNAME_RE.match(text) else None


def new_secret(size=48):
    return secrets.token_urlsafe(size)


def challenge(verifier):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def authorize_url(state, verifier, install_id):
    return Config.STATBATE_BASE + "/oauth/authorize?" + urlencode({
        "client_id": Config.STATBATE_CLIENT_ID,
        "redirect_uri": Config.REDIRECT_URI,
        "response_type": "code",
        "code_challenge": challenge(verifier),
        "code_challenge_method": "S256",
        "install_id": install_id,
        "scope": Config.SCOPES,
        "state": state,
    })


def parse_room(username, data):
    users = []
    for user in data.get("users") or []:
        if not isinstance(user, dict) or not user.get("username"):
            continue
        users.append({
            "username": str(user["username"]),
            "hour": int(user.get("tipsHour") or 0),
            "day": int(user.get("tipsDay") or 0),
            "month": int(user.get("tipsThirtyDays") or 0),
            "all_time": int(user.get("allTimeTokens") or 0),
        })
    users.sort(key=lambda u: (-u["day"], -u["month"], -u["all_time"], u["username"].lower()))
    return {
        "username": username,
        "online": True,
        "cached_at": data.get("cached_at"),
        "viewers": len(users),
        "tokens_hour": sum(u["hour"] for u in users),
        "tokens_day": sum(u["day"] for u in users),
        "users": users,
    }


class StatbateClient:
    def __init__(self):
        self.http = httpx.AsyncClient(base_url=Config.STATBATE_BASE, timeout=15)

    async def close(self):
        await self.http.aclose()

    async def _token(self, form):
        form["client_id"] = Config.STATBATE_CLIENT_ID
        response = await self.http.post("/api/oauth/token", data=form)
        if response.status_code in (400, 401, 403):
            raise SignInRequired(response.text[:200])
        response.raise_for_status()
        return response.json()

    async def exchange_code(self, code, verifier):
        return await self._token({
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": Config.REDIRECT_URI,
        })

    async def refresh(self, refresh_token):
        return await self._token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })

    async def revoke(self, refresh_token):
        try:
            await self.http.post("/api/oauth/revoke", data={
                "client_id": Config.STATBATE_CLIENT_ID, "token": refresh_token,
            })
        except httpx.HTTPError:
            pass

    async def _get(self, access_token, path):
        response = await self.http.get(
            path, headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 401:
            raise SignInRequired()
        if response.status_code == 403:
            raise PlanRequired()
        if response.status_code == 429:
            raise RateLimited()
        return response

    async def account(self, access_token):
        response = await self._get(access_token, "/api/me/account")
        response.raise_for_status()
        return response.json()

    async def room(self, access_token, username):
        """Espectadores de una sala y lo que ha dado cada uno."""
        response = await self._get(
            access_token, f"/api/room/{Config.SITE}/{username}/online-users"
        )
        if response.status_code == 404:  # desconectada o inexistente
            return {"username": username, "online": False, "viewers": 0,
                    "tokens_hour": 0, "tokens_day": 0, "users": [], "cached_at": None}
        response.raise_for_status()
        return parse_room(username, response.json())
