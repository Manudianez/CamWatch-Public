"""Vigilancia en segundo plano de los modelos registrados."""

import asyncio
import time
from datetime import datetime, timezone

import httpx

from . import model_manager
from .logger import logger
from .stripchat import ModelNotFound, StripchatClient

POLL_SECONDS = 4
CHATTER_WINDOW = 15 * 60  # se considera "en el chat" quien escribió en los últimos 15 min


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_start_iso():
    midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Monitor:
    def __init__(self):
        self.client = StripchatClient()
        self.states = {}
        self._task = None

    def _new_state(self, username, last_seen=None):
        return {
            "username": username,
            "status": "unknown",
            "status_label": "Comprobando…",
            "online": False,
            "viewers": None,
            "topic": "",
            "avatar": "",
            "last_seen": last_seen,
            "checked_at": None,
            "error": None,
            "viewer_names": None,   # lista completa, si Stripchat la entrega
            "chatters": {},         # usuario -> último instante en que escribió
            "members_supported": True,
        }

    def start(self):
        for row in model_manager.list_models():
            self.states[row[1]] = self._new_state(row[1], row[4])
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
        await self.client.close()

    def add(self, username):
        added = model_manager.add_model(username)
        if username not in self.states:
            self.states[username] = self._new_state(username)
            asyncio.create_task(self._poll(username))
        return added

    def remove(self, username):
        model_manager.remove_model(username)
        self.states.pop(username, None)

    async def _loop(self):
        while True:
            await asyncio.gather(*(self._poll(name) for name in list(self.states)))
            await asyncio.sleep(POLL_SECONDS)

    async def _poll(self, username):
        state = self.states.get(username)
        if state is None:
            return
        try:
            cam = await self.client.cam(username)
            state.update(
                status=cam["status"],
                status_label=cam["status_label"],
                online=cam["online"],
                viewers=cam["viewers"] if cam["online"] else 0,
                topic=cam["topic"],
                avatar=cam["avatar"] or state["avatar"],
                error=None,
            )
            if cam["online"]:
                state["last_seen"] = _now_iso()
                await self._poll_chat(username, state)
                await self._poll_members(username, state)
            else:
                state["viewer_names"] = None
                state["chatters"] = {}
            model_manager.update_status(username, cam["status"], state["last_seen"])
        except ModelNotFound:
            state.update(
                status="notfound", status_label="No existe", online=False,
                error="Stripchat no conoce a esta modelo. Revisa el nombre.",
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            state["error"] = f"No se pudo consultar Stripchat ({type(error).__name__})"
            logger.warning(f"{username}: {error!r}")
        state["checked_at"] = _now_iso()

    async def _poll_chat(self, username, state):
        try:
            messages = await self.client.chat(username)
        except (ModelNotFound, httpx.HTTPError, ValueError) as error:
            logger.warning(f"{username} (chat): {error!r}")
            return
        now = time.time()
        seen = state.setdefault("_seen", set())
        for msg in messages:
            if msg["id"] in seen:
                continue
            seen.add(msg["id"])
            if msg["type"] == "tip" and msg["amount"] > 0:
                model_manager.add_tip(
                    username, msg["id"], msg["username"], msg["amount"],
                    msg["body"], msg["created_at"] or _now_iso(),
                )
            if msg["username"] and msg["username"] != "Anónimo" and not msg["is_model"]:
                state["chatters"][msg["username"]] = now
        state["chatters"] = {
            name: seen for name, seen in state["chatters"].items()
            if now - seen < CHATTER_WINDOW
        }
        if len(state["_seen"]) > 5000:
            state["_seen"] = {m["id"] for m in messages}

    async def _poll_members(self, username, state):
        if not state["members_supported"]:
            return
        try:
            state["viewer_names"] = await self.client.members(username)
        except (ModelNotFound, httpx.HTTPError, ValueError):
            # Stripchat no entrega la lista sin sesión: no se vuelve a pedir.
            state["members_supported"] = False
            state["viewer_names"] = None

    def snapshot(self):
        today_start = _today_start_iso()
        models = []
        for username in sorted(self.states, key=str.lower):
            state = self.states[username]
            public = {k: v for k, v in state.items()
                      if k not in ("chatters", "members_supported", "_seen")}
            public["chatters"] = [
                name for name, _ in
                sorted(state["chatters"].items(), key=lambda item: -item[1])
            ]
            public["tips"] = model_manager.tip_summary(username, today_start)
            models.append(public)
        return {"models": models, "poll_seconds": POLL_SECONDS}
