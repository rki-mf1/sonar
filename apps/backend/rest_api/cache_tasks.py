"""
Cache invalidation and rebuild tasks for the Sonar backend.

After a successful data import, cached API responses become stale. These tasks
flush the relevant Redis keys so that subsequent API requests return fresh data.

Cache Architecture
------------------
- Redis DB 0: Celery broker & result backend (NEVER flushed by these tasks)
- Redis DB 1: Django cache (``CACHES["default"]``)

Key Prefixes
~~~~~~~~~~~~
- ``serialized-cache:<md5>`` — full serialized page responses
  (set by ``SerializedOutputCachePagination`` in ``customDRF.py``)
- ``query-count:<md5>`` — cached COUNT(*) results
  (set by ``CachedCountQueryset`` in ``customDRF.py``)

TTL is controlled by ``settings.CACHE_OBJECT_TTL`` (default 3600 s = 1 hour).
"""

import logging

from celery import shared_task
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

# Key prefixes used across all caching layers:
# - customDRF.py  : SerializedOutputCachePagination, CachedCountQueryset
# - viewsets.py   : get_all_properties()
# - viewsets_statistics_and_plots.py : get_metadata_coverage(), _get_grouped_lineages_per_week()
CACHE_KEY_PREFIXES = (
    "serialized-cache:*",
    "query-count:*",
    "all_properties:*",
    "metadata_coverage:*",
    "grouped_lineages_per_week:*",
)


def _flush_cache_keys() -> int:
    """Delete all ``serialized-cache:*`` and ``query-count:*`` keys from
    the default Django cache (Redis DB 1).

    Uses ``SCAN`` instead of ``KEYS`` to avoid blocking Redis on large
    key-spaces.

    Returns the total number of keys deleted.
    """
    conn = get_redis_connection("default")
    deleted = 0

    for prefix in CACHE_KEY_PREFIXES:
        # django_redis prepends its own key prefix (e.g. ":1:"), so we
        # need the full pattern. The default prefix from django_redis is
        # typically "" or ":1:" depending on KEY_PREFIX / VERSION settings.
        # We search for any key ending with our prefix pattern.
        # Build the full pattern: the django_redis default key format is
        # `:version:key`, but we just wildcard-match the suffix.
        pattern = f"*{prefix}"
        cursor = 0
        while True:
            cursor, keys = conn.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                deleted += conn.delete(*keys)
            if cursor == 0:
                break

    return deleted


@shared_task(name="rest_api.invalidate_query_cache")
def invalidate_query_cache():
    """Celery task: flush all stale query / response cache keys.

    Intended to be dispatched at the end of a successful data import so
    that API consumers immediately see fresh results.
    """
    deleted = _flush_cache_keys()
    logger.info(
        "Cache invalidation complete — deleted %d key(s) " "(prefixes: %s)",
        deleted,
        ", ".join(CACHE_KEY_PREFIXES),
    )
    return {"deleted_keys": deleted}
