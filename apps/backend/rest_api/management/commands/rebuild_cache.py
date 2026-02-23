"""
Management command to invalidate (and optionally rebuild) the API query cache.

Usage
-----
::

    # Flush all cached query-count and serialized-cache keys from Redis DB 1
    python manage.py rebuild_cache

    # Also display per-prefix deletion counts
    python manage.py rebuild_cache --verbose

This command is an operator escape-hatch that does **not** depend on Celery.
It can be run from the Django container or any host that has direct access
to the Redis instance.

See ``rest_api/cache_tasks.py`` for the underlying implementation and cache
architecture documentation.
"""

from django.core.management.base import BaseCommand

from rest_api.cache_tasks import _flush_cache_keys
from rest_api.cache_tasks import CACHE_KEY_PREFIXES


class Command(BaseCommand):
    help = (
        "Invalidate all API query caches (serialized-cache:* and "
        "query-count:* keys in Redis DB 1). Run this after a manual "
        "data import or whenever stale API responses are observed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            default=False,
            help="Print detailed deletion counts.",
        )

    def handle(self, *args, **options):
        deleted = _flush_cache_keys()

        if options["verbose"]:
            self.stdout.write(f"Scanned prefixes: {', '.join(CACHE_KEY_PREFIXES)}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Cache invalidation complete — {deleted} key(s) deleted."
            )
        )
