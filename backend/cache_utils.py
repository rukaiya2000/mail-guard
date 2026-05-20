import hashlib
from datetime import datetime, timedelta

_cache: dict[str, dict] = {}


def hash_email(email_text: str) -> str:
    return hashlib.sha256(email_text.encode()).hexdigest()


def get_cached_classification(email_hash: str, user_id: str = None, cache_hours: int = 24) -> dict | None:
    entry = _cache.get(email_hash)
    if not entry:
        return None
    cutoff = datetime.utcnow() - timedelta(hours=cache_hours)
    if entry["timestamp"] < cutoff:
        del _cache[email_hash]
        return None
    return entry


def cache_classification(email_hash: str, result: dict):
    _cache[email_hash] = {**result, "timestamp": datetime.utcnow()}
