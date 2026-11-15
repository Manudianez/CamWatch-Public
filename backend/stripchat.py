"""Cliente de la API pública de Stripchat.

Todo lo que depende de cómo responde Stripchat vive en este archivo. Si la
web cambia sus respuestas, este es el único sitio que hay que tocar.
"""

import os
import random
import re

import httpx

BASE_URL = os.getenv("STRIPCHAT_BASE", "https://stripchat.com").rstrip("/")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

STATUS_LABELS = {
    "public": "En directo",
    "private": "En privado",
    "p2p": "En privado",
    "virtualPrivate": "En privado",
    "groupShow": "Show en grupo",
    "idle": "Ausente",
    "off": "Desconectada",
}
LIVE_STATUSES = {"public", "private", "p2p", "virtualPrivate", "groupShow"}


class ModelNotFound(Exception):
    pass


def clean_username(text):
    """Acepta un nombre o una URL de Stripchat y devuelve el nombre, o None."""
    text = (text or "").strip().split("?")[0].rstrip("/")
    if "/" in text:
        text = text.rsplit("/", 1)[1]
    text = text.lstrip("@")
    return text if USERNAME_RE.match(text) else None


def _uniq():
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=16))


def _find(obj, key):
    """Primera aparición (en profundidad) de `key` con valor no nulo."""
    if isinstance(obj, dict):
        if obj.get(key) is not None:
            return obj[key]
        for value in obj.values():
            found = _find(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find(value, key)
            if found is not None:
                return found
    return None


def parse_cam(data):
    user = data.get("user") or {}
    if isinstance(user.get("user"), dict):
        user = user["user"]
    cam = data.get("cam") or {}

    status = user.get("status") or _find(data, "status") or "off"
    is_live = user.get("isLive")
    online = bool(is_live) if is_live is not None else status in LIVE_STATUSES
    if not online and status in LIVE_STATUSES:
        status = "off"

    viewers = cam.get("viewersCount")
    if viewers is None:
        viewers = user.get("viewersCount")
    if viewers is None:
        viewers = _find(data, "viewersCount")

    return {
        "id": user.get("id") or _find(data, "modelId"),
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "online": online,
        "viewers": int(viewers) if isinstance(viewers, (int, float)) else None,
        "topic": cam.get("topic") or _find(data, "topic") or "",
        "avatar": user.get("avatarUrl") or user.get("previewUrlThumbSmall") or "",
    }


def parse_chat(data):
    messages = data.get("messages") if isinstance(data, dict) else data
    result = []
    for msg in messages or []:
        if not isinstance(msg, dict) or msg.get("id") is None:
            continue
        details = msg.get("details") or {}
        user = msg.get("userData") or {}
        amount = details.get("amount")
        is_tip = msg.get("type") == "tip" or isinstance(amount, (int, float))
        username = user.get("username") or ""
        if details.get("isAnonymous") or (is_tip and not username):
            username = "Anónimo"
        result.append({
            "id": str(msg["id"]),
            "type": "tip" if is_tip else (msg.get("type") or "text"),
            "username": username,
            "is_model": bool(user.get("isModel")),
            "amount": int(amount) if is_tip and isinstance(amount, (int, float)) else 0,
            "body": str(details.get("body") or "")[:300],
            "created_at": msg.get("createdAt") or "",
        })
    return result


def parse_members(data):
    members = data.get("members") if isinstance(data, dict) else data
    names = []
    for member in members or []:
        if isinstance(member, dict):
            name = (member.get("user") or member).get("username")
            if name:
                names.append(name)
    return names


class StripchatClient:
    def __init__(self):
        self.http = httpx.AsyncClient(
            base_url=BASE_URL, headers=HEADERS, timeout=10, follow_redirects=True
        )

    async def close(self):
        await self.http.aclose()

    async def _get(self, path):
        response = await self.http.get(path, params={"uniq": _uniq()})
        if response.status_code == 404:
            raise ModelNotFound(path)
        response.raise_for_status()
        return response.json()

    async def cam(self, username):
        """Estado de la emisión: en línea, espectadores, tema."""
        return parse_cam(await self._get(f"/api/front/v2/models/username/{username}/cam"))

    async def chat(self, username):
        """Últimos mensajes del chat público, propinas incluidas."""
        return parse_chat(await self._get(f"/api/front/v2/models/username/{username}/chat"))

    async def members(self, username):
        """Lista de espectadores, si Stripchat la entrega sin iniciar sesión."""
        return parse_members(await self._get(f"/api/front/models/username/{username}/members"))

    async def raw(self, username):
        """Respuestas en bruto, para diagnosticar cambios en la web."""
        out = {}
        for name, path in (
            ("cam", f"/api/front/v2/models/username/{username}/cam"),
            ("chat", f"/api/front/v2/models/username/{username}/chat"),
            ("members", f"/api/front/models/username/{username}/members"),
        ):
            try:
                response = await self.http.get(path, params={"uniq": _uniq()})
                try:
                    body = response.json()
                except ValueError:
                    body = response.text[:2000]
                out[name] = {"http": response.status_code, "body": body}
            except httpx.HTTPError as error:
                out[name] = {"error": repr(error)}
        return out
