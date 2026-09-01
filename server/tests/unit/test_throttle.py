import uuid

import pytest

from core.exceptions import RateLimitedError
from services.analysis import throttle


@pytest.fixture
def user() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def frozen(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(throttle, "_now", lambda: clock["now"])

    def advance(seconds):
        clock["now"] += seconds

    return advance


def _saturate(user, window):
    for _ in range(window.allowed):
        throttle.acquire(user)


def test_a_normal_pace_is_never_refused(user, frozen):
    for _ in range(6):
        throttle.acquire(user)
        frozen(300)

    assert throttle.spent(user) < throttle.HOUR.allowed


def test_a_burst_is_refused_with_a_delay(user, frozen):
    _saturate(user, throttle.MINUTE)

    with pytest.raises(RateLimitedError) as error:
        throttle.acquire(user)

    assert error.value.status_code == 429
    assert error.value.code == "scan_throttled"
    assert 0 < error.value.retry_after <= 60
    assert error.value.headers["Retry-After"] == str(error.value.retry_after)
    assert "seconds" in error.value.message
    assert error.value.params == {"seconds": error.value.retry_after}


def test_the_minute_window_reopens_on_time(user, frozen):
    _saturate(user, throttle.MINUTE)
    frozen(61)

    throttle.acquire(user)


def test_the_hourly_ceiling_holds_beyond_the_minute(user, frozen):
    for _ in range(throttle.HOUR.allowed):
        throttle.acquire(user)
        frozen(60)

    with pytest.raises(RateLimitedError) as error:
        throttle.acquire(user)

    assert error.value.retry_after > 60


def test_the_hourly_ceiling_reopens_after_an_hour(user, frozen):
    for _ in range(throttle.HOUR.allowed):
        throttle.acquire(user)
        frozen(60)

    frozen(3600)
    throttle.acquire(user)


def test_a_cache_hit_costs_nothing(user, frozen):
    _saturate(user, throttle.MINUTE)
    throttle.refund(user)

    throttle.acquire(user)


def test_users_are_counted_apart(user, frozen):
    other = uuid.uuid4()
    _saturate(user, throttle.MINUTE)

    throttle.acquire(other)

    assert throttle.spent(other) == 1


@pytest.mark.asyncio
async def test_a_cached_run_gives_its_slot_back(user, frozen):
    _saturate(user, throttle.MINUTE)
    before = throttle.spent(user)

    async def source():
        yield {"event": "progress", "step": "scanning", "cached": True}
        yield {"event": "done"}

    events = [event async for event in throttle.metered(user, source)()]

    assert len(events) == 2
    assert throttle.spent(user) == before - 1


@pytest.mark.asyncio
async def test_a_real_run_keeps_its_slot(user, frozen):
    throttle.acquire(user)
    before = throttle.spent(user)

    async def source():
        yield {"event": "progress", "step": "scanning"}
        yield {"event": "done"}

    async for _ in throttle.metered(user, source)():
        pass

    assert throttle.spent(user) == before
