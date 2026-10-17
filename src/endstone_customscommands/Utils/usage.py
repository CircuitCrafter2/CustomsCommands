"""Persistent usage counters for usage limits (data/usage.json)."""

import json
import math
import os
import time

from . import paths


class UsageTracker:
    """
    Counts how many times each player used each command.

    A limit is {"uses": N, "period": seconds}: a player may use the command N times, then
    has to wait until `period` seconds after their first use of the current window have
    passed (period 0 = the counter never resets). Times are wall-clock so they survive
    restarts.
    """

    def __init__(self, clock=time.time):
        self._clock = clock
        self._data = None

    def _path(self):
        return paths.file("data", "usage.json")

    def _load(self) -> dict:
        if self._data is None:
            try:
                with open(self._path(), "r", encoding="utf-8") as f:
                    loaded = json.load(f)
            except (OSError, ValueError):
                loaded = {}
            self._data = loaded if isinstance(loaded, dict) else {}
        return self._data

    def _save(self) -> None:
        path = os.fspath(self._path())
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            temporary = path + ".tmp"
            with open(temporary, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
            os.replace(temporary, path)
        except OSError:
            pass

    def reload(self) -> None:
        self._data = None

    def _state(self, command: str, player_key: str, period: int):
        entry = self._load().get(command, {}).get(player_key)
        if not isinstance(entry, dict):
            return None
        count, start = entry.get("count"), entry.get("start")
        if not isinstance(count, int) or not isinstance(start, (int, float)):
            return None
        if period > 0 and self._clock() - start >= period:
            return None  # the window is over
        return entry

    def blocked(self, command: str, player_key: str, limit: dict):
        """None if the player may use the command, else the seconds left (-1 = never)."""
        period = limit.get("period", 0)
        entry = self._state(command, player_key, period)
        if entry is None or entry["count"] < limit["uses"]:
            return None
        if period <= 0:
            return -1
        return max(1, math.ceil(entry["start"] + period - self._clock()))

    def record(self, command: str, player_key: str, limit: dict) -> None:
        period = limit.get("period", 0)
        entry = self._state(command, player_key, period)
        per_command = self._load().setdefault(command, {})
        if entry is None:
            per_command[player_key] = {"count": 1, "start": self._clock()}
        else:
            entry["count"] += 1
        self._save()

    def reset(self, command: str) -> None:
        if self._load().pop(command, None) is not None:
            self._save()

    def rename(self, old: str, new: str) -> None:
        data = self._load()
        if old in data and old != new:
            data[new] = data.pop(old)
            self._save()


USAGE = UsageTracker()
