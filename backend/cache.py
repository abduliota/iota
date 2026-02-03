"""In-memory semantic response cache. Phase 0."""
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import math

_entries: List[Tuple[List[float], str, List[Dict], datetime]] = []
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "86400"))
MAX_ENTRIES = 500


def _cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_cached_response(query_embedding: List[float], threshold: float = 0.95) -> Optional[Tuple[str, List[Dict]]]:
    now = datetime.now()
    for cached_emb, response_text, references, expires_at in _entries:
        if expires_at < now:
            continue
        if _cosine_sim(query_embedding, cached_emb) >= threshold:
            return (response_text, references)
    return None


def set_cached_response(query_embedding: List[float], response_text: str, references: List[Dict], ttl_seconds: int = None):
    if ttl_seconds is None:
        ttl_seconds = CACHE_TTL_SECONDS
    expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
    _entries.append((list(query_embedding), response_text, references, expires_at))
    # Simple cleanup
    while len(_entries) > MAX_ENTRIES:
        _entries.pop(0)
