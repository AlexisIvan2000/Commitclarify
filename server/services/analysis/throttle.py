import logging
import time
import uuid

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from core.config import SCAN_RATE_PER_HOUR, SCAN_RATE_PER_MINUTE
from core.exceptions import RateLimitedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Window:
    span: float
    allowed: int
    label: str


MINUTE = Window(60.0, SCAN_RATE_PER_MINUTE, "minute")
HOUR = Window(3600.0, SCAN_RATE_PER_HOUR, "heure")

WINDOWS = (MINUTE, HOUR)
LONGEST = max(window.span for window in WINDOWS)

_hits: dict[uuid.UUID, list[float]] = {}


def _now() -> float:
    return time.monotonic()


def _recent(user_id: uuid.UUID, now: float) -> list[float]:
    kept = [at for at in _hits.get(user_id, []) if now - at < LONGEST]

    if kept:
        _hits[user_id] = kept
    else:
        _hits.pop(user_id, None)

    return kept


def _wait_for(hits: list[float], now: float, window: Window) -> float | None:
    inside = [at for at in hits if now - at < window.span]

    if len(inside) < window.allowed:
        return None

    return window.span - (now - inside[-window.allowed])


def acquire(user_id: uuid.UUID) -> None:
    now = _now()
    hits = _recent(user_id, now)

    for window in WINDOWS:
        wait = _wait_for(hits, now, window)

        if wait is not None:
            logger.warning(
                "Cadence de scan depassee pour l'utilisateur %s (%d par %s)",
                user_id, window.allowed, window.label,
            )
            raise RateLimitedError(
                f"Trop de scans lances coup sur coup. Reessayez dans {max(1, round(wait))} secondes.",
                code="scan_throttled",
                retry_after=wait,
            )

    _hits.setdefault(user_id, []).append(now)


def refund(user_id: uuid.UUID) -> None:
    hits = _hits.get(user_id)

    if hits:
        hits.pop()
        logger.info("Scan servi par le cache : cadence non decomptee pour %s", user_id)

    if not _hits.get(user_id):
        _hits.pop(user_id, None)


def spent(user_id: uuid.UUID) -> int:
    return len(_recent(user_id, _now()))


def forget(user_id: uuid.UUID) -> None:
    _hits.pop(user_id, None)


Source = Callable[[], AsyncIterator[dict]]


def metered(user_id: uuid.UUID, source: Source) -> Source:
    async def wrapped() -> AsyncIterator[dict]:
        refunded = False

        async for event in source():
            if event.get("cached") and not refunded:
                refunded = True
                refund(user_id)

            yield event

    return wrapped
