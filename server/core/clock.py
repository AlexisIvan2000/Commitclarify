from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def start_of_day(moment: datetime | None = None) -> datetime:
    return (moment or utcnow()).replace(hour=0, minute=0, second=0, microsecond=0)

def in_minutes(minutes: int) -> datetime:
    return utcnow() + timedelta(minutes=minutes)

def in_days(days: int) -> datetime:
    return utcnow() + timedelta(days=days)

def in_seconds(seconds: int) -> datetime:
    return utcnow() + timedelta(seconds=seconds)
