"""Servidor web de StripWatch.  Arranque:  python -m backend.server"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import Config
from .database import initialize_database
from .monitor import Monitor
from .stripchat import clean_username

APP_DIR = Path(__file__).resolve().parent.parent / "app"

monitor = Monitor()


@asynccontextmanager
async def lifespan(app):
    initialize_database()
    monitor.start()
    yield
    await monitor.stop()


app = FastAPI(title=Config.APP_NAME, version=Config.VERSION, lifespan=lifespan)


class NewModel(BaseModel):
    username: str


@app.get("/")
def index():
    return FileResponse(APP_DIR / "index.html")


@app.get("/api/state")
async def state():
    return monitor.snapshot()


@app.post("/api/models")
async def add_model(body: NewModel):
    username = clean_username(body.username)
    if not username:
        raise HTTPException(400, "Nombre no válido. Usa el nombre tal como sale en la URL de Stripchat.")
    existing = next((n for n in monitor.states if n.lower() == username.lower()), None)
    if existing:
        raise HTTPException(409, f"Ya estás siguiendo a {existing}.")
    monitor.add(username)
    return {"username": username}


@app.delete("/api/models/{username}")
async def remove_model(username: str):
    monitor.remove(username)
    return {"ok": True}


@app.get("/api/debug/{username}")
async def debug(username: str):
    username = clean_username(username)
    if not username:
        raise HTTPException(400, "Nombre no válido.")
    return await monitor.client.raw(username)


def main():
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
