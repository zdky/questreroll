"""Tiny JSON "database" (auth.json) with an in-memory cache.

All changes go through one asyncio.Lock, so concurrent handlers can't
overwrite each other's data, and the file is replaced atomically,
so a crash in the middle of a write can't corrupt it.
"""

import asyncio
import copy
import os

import orjson

from constants import BASE_DIR
from utils import log

AUTH_PATH = BASE_DIR / "auth.json"


def new_user(lang: str = "en") -> dict:
    return {
        "lang": lang,
        "acc_token": {},
        "fn_token": {},
        "buttons": {},
        "msg_for_del": [],
        "first_quest_msg": "",
        "stats": {"quest": 0, "skips": 0},
    }


class Database:
    def __init__(self, path=AUTH_PATH):
        self.path = path
        self._lock = asyncio.Lock()
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")
            return {}
        data = orjson.loads(self.path.read_bytes() or b"{}")
        # fill fields added in newer versions
        for user_id, user in data.items():
            data[user_id] = new_user() | user
        return data

    def _save(self) -> None:
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_bytes(orjson.dumps(self._data, option=orjson.OPT_INDENT_2))
        os.replace(tmp_path, self.path)

    def user_ids(self) -> list[int]:
        return [int(user_id) for user_id in self._data]

    def get(self, user_id: int) -> dict | None:
        """Copy of user data or None if user isn't registered."""
        user = self._data.get(str(user_id))
        return copy.deepcopy(user) if user is not None else None

    async def add_user(self, user_id: int, lang: str) -> None:
        async with self._lock:
            self._data[str(user_id)] = new_user(lang)
            await asyncio.to_thread(self._save)

    async def update(self, user_id: int, **fields) -> None:
        """Set user fields, e.g. update(user_id, lang="ru", buttons={})"""
        async with self._lock:
            user = self._data.get(str(user_id))
            if user is None:
                log.warning(f"update(): user_id {user_id} isn't in auth.json")
                return
            user.update(copy.deepcopy(fields))
            await asyncio.to_thread(self._save)

    async def add_msg_for_del(self, user_id: int, msg_id: int) -> None:
        async with self._lock:
            user = self._data.get(str(user_id))
            if user is not None:
                user["msg_for_del"].append(msg_id)
                await asyncio.to_thread(self._save)

    async def pop_msgs_for_del(self, user_id: int) -> list[int]:
        async with self._lock:
            user = self._data.get(str(user_id))
            if not user or not user["msg_for_del"]:
                return []
            msgs, user["msg_for_del"] = user["msg_for_del"], []
            await asyncio.to_thread(self._save)
            return msgs

    async def inc_stat(self, user_id: int, stat: str) -> None:
        """+1 to user stats: stat = "quest" / "skips" """
        async with self._lock:
            user = self._data.get(str(user_id))
            if user is not None:
                user["stats"][stat] = user["stats"].get(stat, 0) + 1
                await asyncio.to_thread(self._save)


db = Database()
