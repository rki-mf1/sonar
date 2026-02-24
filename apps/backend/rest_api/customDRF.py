import hashlib

from django.conf import settings
from django.core.cache import caches
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param
from rest_framework.utils.urls import replace_query_param


# ------------- Method 4, this is a simple method to cache the count of a queryset
def CachedCountQueryset(
    queryset, timeout=getattr(settings, "CACHE_OBJECT_TTL", 3600), cache_name="default"
):
    """
    This method we cache only count of a queryset, but not the result from whole queryset.
    (Surprisingly improved the performance of the API)

    Return copy of queryset with queryset.count() wrapped to cache result for `timeout` seconds.
    """
    cache = caches[cache_name]
    queryset = queryset._chain()
    real_count = queryset.count

    def count(queryset):
        cache_key = (
            "query-count:" + hashlib.md5(str(queryset.query).encode("utf8")).hexdigest()
        )
        print(f"Cache key for count: {cache_key}")
        # return existing value, if any
        value = cache.get(cache_key)
        if value is not None:
            return value

        # cache new value
        value = real_count()
        cache.set(cache_key, value, timeout)
        return value

    queryset.count = count.__get__(queryset, type(queryset))
    return queryset


class CachedCountLimitOffsetPagination(LimitOffsetPagination):
    def paginate_queryset(self, queryset, *args, **kwargs):
        if hasattr(queryset, "count"):
            queryset = CachedCountQueryset(queryset)
        return super().paginate_queryset(queryset, *args, **kwargs)

    def get_paginated_response(self, data):
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
                "count": getattr(self, "count", None),  # Include count if available
            }
        )


# ------------- Method 6 - Serialized Output Cache + COUNT queries cached (shared across pages)
class SerializedOutputCachePagination(LimitOffsetPagination):
    """method 6
    Two-Level Caching:
    - Level 1: COUNT queries cached (shared across pages) (similar to method 4)
    - Level 2: Full serialized responses cached (page-specific caching, doesn't cache entire dataset)
    * Caches the final serialized output (JSON) instead of just the queryset,
    so the expensive serializer processing work (database queries) will not be repeated.


    NOTE:
    1. we still have to find the better way for cache timeout
    """

    # Use CACHE_OBJECT_TTL from settings for consistency across all caching layers.
    cache_timeout = getattr(settings, "CACHE_OBJECT_TTL", 3600)

    cache_name = "default"

    def paginate_queryset(self, queryset, request, view=None):
        self.offset = self.get_offset(request)
        self.limit = self.get_limit(request)
        self.request = request

        # Try to get fully cached response first (serialized data + metadata)
        cache_key = self._generate_cache_key(queryset, request)
        cache = caches[self.cache_name]

        cached_response = cache.get(cache_key)
        if cached_response is not None:
            # print(f"Cache HIT for serialized output: {cache_key}")
            # Restore all pagination state from cache
            self.count = cached_response["count"]
            self.has_next = cached_response["has_next"]
            self.has_previous = cached_response["has_previous"]
            self.cached_serialized_data = cached_response["serialized_data"]
            # Return empty list since we'll use cached serialized data
            return []

        # print(f"No Cache for serialized output: {cache_key}")

        # Cache miss - need to fetch and serialize
        # First, get cached count using the cached count queryset
        queryset_with_cached_count = CachedCountQueryset(
            queryset, self.cache_timeout, self.cache_name
        )

        # Get the total count (this will be cached)
        total_count = queryset_with_cached_count.count()

        # Get the actual results for this page
        results = list(queryset[self.offset : self.offset + self.limit])

        # Calculate pagination state
        has_next = (self.offset + self.limit) < total_count
        has_previous = self.offset > 0

        # Set instance attributes for immediate use
        self.count = total_count
        self.has_next = has_next
        self.has_previous = has_previous
        self.cached_serialized_data = None  # Will be set by ViewSet

        # Store for later caching
        self._current_cache_key = cache_key

        return results

    def cache_serialized_response(self, serialized_data):
        """Call this method from ViewSet after serialization to cache the final output"""
        if hasattr(self, "_current_cache_key"):
            cache = caches[self.cache_name]
            cache_data = {
                "serialized_data": serialized_data,
                "count": self.count,
                "has_next": self.has_next,
                "has_previous": self.has_previous,
            }
            cache.set(self._current_cache_key, cache_data, self.cache_timeout)

    def _generate_cache_key(self, queryset, request):
        """Generate cache key based on query + pagination params"""
        # Include SQL query, offset, limit, and any filters
        query_str = str(queryset.query)
        offset = self.get_offset(request)
        limit = self.get_limit(request)

        # Include common filter parameters
        filters = {}
        for key, value in request.query_params.items():
            if key not in ["offset", "limit"]:  # Exclude pagination params
                filters[key] = value

        cache_content = f"{query_str}|{offset}|{limit}|{filters}"
        cache_hash = hashlib.md5(cache_content.encode("utf-8")).hexdigest()
        return f"serialized-cache:{cache_hash}"

    def get_paginated_response(self, data):
        # If we have cached serialized data, use it instead of the passed data
        if (
            hasattr(self, "cached_serialized_data")
            and self.cached_serialized_data is not None
        ):
            response_data = self.cached_serialized_data
        else:
            response_data = data
            # Cache the serialized data for future requests
            self.cache_serialized_response(data)

        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": response_data,
                "count": getattr(self, "count", None),
            }
        )

    def get_next_link(self):
        if not getattr(self, "has_next", False):
            return None

        url = self.request.build_absolute_uri()
        offset = self.offset + self.limit
        return replace_query_param(url, self.offset_query_param, offset)

    def get_previous_link(self):
        if not getattr(self, "has_previous", False):
            return None

        url = self.request.build_absolute_uri()
        offset = self.offset - self.limit
        if offset <= 0:
            return remove_query_param(url, self.offset_query_param)
        return replace_query_param(url, self.offset_query_param, offset)
