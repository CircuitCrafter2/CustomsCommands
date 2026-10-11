import math
import time


class CooldownTracker:
    """In-memory cooldowns. Reset when the server restarts or reloads."""

    MAX_ENTRIES = 5000

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._expiry = {}

    def remaining(self, key) -> int:
        """Whole seconds left (rounded up), 0 if the cooldown is over."""
        expiry = self._expiry.get(key)
        if expiry is None:
            return 0
        left = expiry - self._clock()
        if left <= 0:
            del self._expiry[key]
            return 0
        return math.ceil(left)

    def start(self, key, seconds: int):
        if len(self._expiry) >= self.MAX_ENTRIES:
            now = self._clock()
            self._expiry = {k: e for k, e in self._expiry.items() if e > now}
        self._expiry[key] = self._clock() + seconds

    def clear(self):
        self._expiry.clear()


COOLDOWNS = CooldownTracker()
