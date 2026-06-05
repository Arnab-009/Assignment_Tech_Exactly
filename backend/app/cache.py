"""In-memory, TTL-based result cache keyed by session id.

This is intentionally simple and process-local — perfect for a single-instance
deployment or the take-home demo. The production upgrade path is to swap this
class for a Redis-backed implementation behind the same interface.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

from app.models.schemas import SummarizeResponse


@dataclass
class _Entry:
    value: SummarizeResponse
    expires_at: float


class ResultStore:
    """Thread-safe store for the latest summarization result per session."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._results: dict[str, _Entry] = {}
        self._last_run: dict[str, float] = {}
        self._lock = threading.Lock()

    def save(self, session_id: str, result: SummarizeResponse) -> None:
        with self._lock:
            self._purge_expired_locked()
            self._results[session_id] = _Entry(
                value=result, expires_at=time.monotonic() + self._ttl
            )

    def get(self, session_id: str) -> Optional[SummarizeResponse]:
        with self._lock:
            entry = self._results.get(session_id)
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                self._results.pop(session_id, None)
                return None
            return entry.value

    def mark_run(self, session_id: str) -> None:
        with self._lock:
            self._last_run[session_id] = time.monotonic()

    def seconds_since_last_run(self, session_id: str) -> Optional[float]:
        with self._lock:
            ts = self._last_run.get(session_id)
            return None if ts is None else time.monotonic() - ts

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._results.pop(session_id, None)
            self._last_run.pop(session_id, None)

    def _purge_expired_locked(self) -> None:
        now = time.monotonic()
        expired = [k for k, e in self._results.items() if e.expires_at < now]
        for key in expired:
            self._results.pop(key, None)
