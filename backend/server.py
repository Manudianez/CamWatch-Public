"""Servidor web de StripWatch y ChaturWatch.  Arranque:  python -m backend.server"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from . import database as db
from .config import Config
from .logger import logger
from .statbate import (
    PlanRequired, RateLimited, SignInRequired, StatbateClient,
    authorize_url, clean_username, new_secret,
)

APP_DIR = Path(__file__).resolve().parent.parent / "app"
SECURE = Config.PUBLIC_URL.startswith("https://")
YEAR = 365 * 24 * 3600
# Las cookies de localhost se comparten entre puertos: cada app usa las suyas.
COOKIE_SESSION = f"{Config.APP}_session"
COOKIE_INSTALL = f"{Config.APP}_install"

statbate = StatbateClient()
refresh_locks = {}   # sid -> candado: una sola renovación en curso por sesión
room_cache = {}      # (cuenta, modelo) -> (instante, datos)


@asynccontextmanager
async def lifespan(app):
    db.initialize_database()
    if not Config.STATBATE_CLIENT_ID:
        logger.warning("Falta STATBATE_CLIENT_ID: el inicio de sesión no funcionará.")
    yield
    await statbate.close()


app = FastAPI(title=Config.APP_NAME, version=Config.VERSION, lifespan=lifespan)


def set_cookie(response, name, value, max_age):
    response.set_cookie(name, value, max_age=max_age, httponly=True,
                        secure=SECURE, samesite="lax", path="/")


def signed_in(request):
    session = db.get_session(request.cookies.get(COOKIE_SESSION))
    if not session or not session.get("refresh_token"):
        raise HTTPException(401, "Inicia sesión con Statbate.")
    return session


def sign_out(session):
    db.delete_session(session["sid"])
    refresh_locks.pop(session["sid"], None)
    for key in [k for k in room_cache if k[0] == session.get("account_id")]:
        room_cache.pop(key, None)


def store_tokens(session, tokens):
    session["access_token"] = tokens["access_token"]
    session["refresh_token"] = tokens["refresh_token"]
    session["expires_at"] = time.time() + int(tokens.get("expires_in", 3600))
    db.save_session(session)


async def access_token(session, force=False):
    """Devuelve un token válido, renovándolo si está a punto de caducar."""
    lock = refresh_locks.setdefault(session["sid"], asyncio.Lock())
    async with lock:
        current = db.get_session(session["sid"]) or session
        if not force and (current.get("expires_at") or 0) - 60 > time.time():
            return current["access_token"]
        try:
            store_tokens(current, await statbate.refresh(current["refresh_token"]))
        except SignInRequired:
            sign_out(current)
            raise HTTPException(401, "La sesión ha caducado. Vuelve a entrar con Statbate.")
        return current["access_token"]


async def call(session, method, *args):
    """Llama a Statbate; ante un 401 renueva una vez y reintenta."""
    try:
        return await method(await access_token(session), *args)
    except SignInRequired:
        try:
            return await method(await access_token(session, force=True), *args)
        except SignInRequired:
            sign_out(session)
            raise HTTPException(401, "La sesión ha caducado. Vuelve a entrar con Statbate.")


# ---------- páginas e inicio de sesión ----------

@app.get("/", response_class=HTMLResponse)
def index():
    page = (APP_DIR / "index.html").read_text(encoding="utf-8")
    for key, value in (("APP_NAME", Config.APP_NAME), ("PLATFORM", Config.PLATFORM),
                       ("MODEL_URL", Config.MODEL_URL), ("ACCENT", Config.ACCENT)):
        page = page.replace("{{" + key + "}}", value)
    return page


@app.get("/oauth/statbate/login")
def login(request: Request):
    if not Config.STATBATE_CLIENT_ID:
        return RedirectResponse("/?error=config", 303)
    install_id = request.cookies.get(COOKIE_INSTALL) or new_secret(24)
    session = db.get_session(request.cookies.get(COOKIE_SESSION)) or {"sid": new_secret(32)}
    session.update(install_id=install_id, state=new_secret(24), verifier=new_secret(64))
    db.save_session(session)
    response = RedirectResponse(
        authorize_url(session["state"], session["verifier"], install_id), 303
    )
    set_cookie(response, COOKIE_SESSION, session["sid"], YEAR)
    set_cookie(response, COOKIE_INSTALL, install_id, YEAR)
    return response


@app.get("/oauth/statbate/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    session = db.get_session(request.cookies.get(COOKIE_SESSION))
    if error or not code:
        return RedirectResponse("/?error=denied", 303)
    if not session or not session.get("state") or state != session["state"]:
        return RedirectResponse("/?error=state", 303)
    verifier = session["verifier"]
    session.update(state=None, verifier=None)
    try:
        store_tokens(session, await statbate.exchange_code(code, verifier))
        account = (await statbate.account(session["access_token"])).get("account") or {}
        session.update(account_id=str(account.get("id")), account_name=account.get("name"))
        db.save_session(session)
    except (SignInRequired, PlanRequired, RateLimited, httpx.HTTPError, KeyError, ValueError) as problem:
        logger.warning(f"Inicio de sesión fallido: {problem!r}")
        db.delete_session(session["sid"])
        return RedirectResponse("/?error=signin", 303)
    return RedirectResponse("/", 303)


@app.post("/api/logout")
async def logout(request: Request):
    session = db.get_session(request.cookies.get(COOKIE_SESSION))
    if session:
        if session.get("refresh_token"):
            await statbate.revoke(session["refresh_token"])
        sign_out(session)
    return {"ok": True}


# ---------- API de la interfaz ----------

@app.get("/api/session")
async def session_info(request: Request):
    base = {"configured": bool(Config.STATBATE_CLIENT_ID), "logged_in": False}
    session = db.get_session(request.cookies.get(COOKIE_SESSION))
    if not session or not session.get("refresh_token"):
        return base
    try:
        # Las capacidades se leen cada vez: el plan puede cambiar sin avisar.
        info = await call(session, statbate.account)
    except HTTPException:
        return base
    except (PlanRequired, RateLimited, httpx.HTTPError, ValueError):
        info = {}
    plan = info.get("plan") or {}
    return {
        "configured": True,
        "logged_in": True,
        "name": (info.get("account") or {}).get("name") or session.get("account_name"),
        "plan": {k: plan.get(k) for k in ("title", "is_trial", "expires_on")},
        "lookups": bool((info.get("capabilities") or {}).get("lookups")),
        "upgrade_url": info.get("upgrade_url") or Config.STATBATE_BASE + "/payment/select",
        "follows": db.list_follows(session["account_id"]),
        "max_follows": Config.MAX_FOLLOWS,
    }


class NewModel(BaseModel):
    username: str


@app.post("/api/models")
async def add_model(body: NewModel, request: Request):
    session = signed_in(request)
    username = clean_username(body.username)
    if not username:
        raise HTTPException(400, f"Nombre no válido. Usa el nombre tal como sale en la URL de {Config.PLATFORM}.")
    follows = db.list_follows(session["account_id"])
    existing = next((n for n in follows if n.lower() == username.lower()), None)
    if existing:
        raise HTTPException(409, f"Ya estás siguiendo a {existing}.")
    if len(follows) >= Config.MAX_FOLLOWS:
        raise HTTPException(409, f"Puedes seguir hasta {Config.MAX_FOLLOWS} modelos a la vez.")
    db.add_follow(session["account_id"], username)
    return {"username": username}


@app.delete("/api/models/{username}")
async def remove_model(username: str, request: Request):
    session = signed_in(request)
    db.remove_follow(session["account_id"], username)
    room_cache.pop((session["account_id"], username), None)
    return {"ok": True}


@app.get("/api/room/{username}")
async def room(username: str, request: Request):
    session = signed_in(request)
    if username not in db.list_follows(session["account_id"]):
        raise HTTPException(404, "No sigues a esta modelo.")
    key = (session["account_id"], username)
    cached = room_cache.get(key)
    if cached and time.time() - cached[0] < Config.ROOM_CACHE_SECONDS:
        return cached[1]
    try:
        data = await call(session, statbate.room, username)
    except PlanRequired:
        raise HTTPException(403, "Tu plan de Statbate no incluye esta consulta.")
    except RateLimited:
        raise HTTPException(429, "Statbate pide ir más despacio. Se reintentará enseguida.")
    except (httpx.HTTPError, ValueError) as problem:
        logger.warning(f"{username}: {problem!r}")
        raise HTTPException(502, "No se pudo consultar Statbate.")
    data["checked_at"] = time.time()
    room_cache[key] = (time.time(), data)
    return data


def main():
    cert, key = os.getenv("SSL_CERTFILE"), os.getenv("SSL_KEYFILE")
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", str(Config.PORT) if cert else "8000")),
        ssl_certfile=cert, ssl_keyfile=key,
    )


if __name__ == "__main__":
    main()
