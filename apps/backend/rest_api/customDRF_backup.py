import hashlib

from django.core.cache import caches
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param
from rest_framework.utils.urls import replace_query_param


# ------------- method 1
class NoCountPagination(LimitOffsetPagination):
    """Custom pagination class that does not return the count of total items.
    It returns only the paginated results without the total count.
    """

    # No need for count, so we override the default behavior
    def get_paginated_response(self, data):
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )

    # Override the default pagination method to not include count
    def paginate_queryset(self, queryset, request, view=None):
        self.offset = self.get_offset(request)
        self.limit = self.get_limit(request)

        # Get one extra element to check if there is a "next" page
        q = list(queryset[self.offset : self.offset + self.limit + 1])
        self.count = self.offset + len(q) if len(q) else self.offset - 1
        if len(q) > self.limit:
            q.pop()

        self.request = request
        if self.count > self.offset + self.limit and self.template is not None:
            self.display_page_controls = True

        return q

    # Override the schema generation to remove count from the response schema
    def get_paginated_response_schema(self, schema):
        ret = super().get_paginated_response_schema(schema)
        del ret["properties"]["count"]
        return ret


# ------------- method 2
class CachedResultsNoCountPagination(LimitOffsetPagination):
    """
    Combines result caching with no-count pagination
    """

    cache_timeout = 60 * 60 * 24  # 1 day cache
    # Cache name to use, default from redis
    cache_name = "default"

    def paginate_queryset(self, queryset, request, view=None):
        self.offset = self.get_offset(request)
        self.limit = self.get_limit(request)

        # Try to get cached results first
        cache_key = self._generate_cache_key(queryset, request)
        cache = caches[self.cache_name]

        cached_page = cache.get(cache_key)
        if cached_page is not None:
            print(f"Cache HIT for: {cache_key}")
            self.request = request
            # Restore pagination state from cache
            self.has_next = cached_page["has_next"]
            self.has_previous = cached_page["has_previous"]
            return cached_page["results"]

        print(f"Cache MISS for: {cache_key}")

        # Cache miss - fetch from database (NoCount style)
        q = list(queryset[self.offset : self.offset + self.limit + 1])

        # Determine if there's a next/previous page
        has_next = len(q) > self.limit
        has_previous = self.offset > 0

        # Cache the page results
        cache_data = {
            "results": q,
            "has_next": has_next,
            "has_previous": has_previous,
        }
        cache.set(cache_key, cache_data, self.cache_timeout)

        self.request = request
        self.has_next = has_next
        self.has_previous = has_previous

        return q

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
        return f"page-cache:{cache_hash}"

    def get_paginated_response(self, data):
        return Response(
            {
                "next": (
                    self.get_next_link() if getattr(self, "has_next", False) else None
                ),
                "previous": (
                    self.get_previous_link()
                    if getattr(self, "has_previous", False)
                    else None
                ),
                "results": data,
                # No count field!
            }
        )

    def get_next_link(self):
        if not getattr(self, "has_next", False):
            return None

        # Build next link manually without using self.count
        url = self.request.build_absolute_uri()
        offset = self.offset + self.limit
        return replace_query_param(url, self.offset_query_param, offset)

    def get_previous_link(self):
        if not getattr(self, "has_previous", False):
            return None

        # Build previous link manually
        url = self.request.build_absolute_uri()
        offset = self.offset - self.limit
        if offset <= 0:
            return remove_query_param(url, self.offset_query_param)
        return replace_query_param(url, self.offset_query_param, offset)

    # Override the schema generation to remove count from the response schema
    def get_paginated_response_schema(self, schema):
        ret = super().get_paginated_response_schema(schema)
        del ret["properties"]["count"]
        return ret


# ------------- method 9
# class CursorPagination(LimitOffsetPagination):
#     def paginate_queryset(self, queryset, request, view=None):
#         # Use ID-based cursor instead of OFFSET
#         cursor = request.query_params.get("cursor")
#         if cursor:
#             queryset = queryset.filter(id__gt=cursor)

#         self.limit = self.get_limit(request)
#         q = list(queryset[: self.limit + 1])

#         if len(q) > self.limit:
#             q.pop()
#             self.next_cursor = q[-1].id if q else None
#         else:
#             self.next_cursor = None

#         return q


# ------------- method 4 (surprisingly good)
def CachedCountQueryset(queryset, timeout=60 * 60, cache_name="default"):
    """
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


# ------------- method 3 - Combined Cache (Count + Results)
class CombinedCachePagination(LimitOffsetPagination):
    """
    Combines both count caching and result caching for maximum performance.
    Caches both the expensive COUNT() query and the actual paginated results.
    """

    cache_timeout = 60 * 60 * 24  # 1 day cache
    cache_name = "default"

    def paginate_queryset(self, queryset, request, view=None):
        self.offset = self.get_offset(request)
        self.limit = self.get_limit(request)
        self.request = request

        # Try to get cached results first
        cache_key = self._generate_cache_key(queryset, request)
        cache = caches[self.cache_name]

        cached_page = cache.get(cache_key)
        if cached_page is not None:
            print(f"Cache HIT for results: {cache_key}")
            # Restore all pagination state from cache
            self.count = cached_page["count"]
            return cached_page["results"]

        print(f"Cache MISS for results: {cache_key}")

        # Cache miss - need to fetch from database
        # First, get cached count using the cached count queryset
        queryset_with_cached_count = CachedCountQueryset(
            queryset, self.cache_timeout, self.cache_name
        )

        # Get the total count (this will be cached)
        total_count = queryset_with_cached_count.count()

        # Get the actual results for this page
        results = list(queryset[self.offset : self.offset + self.limit])

        # Cache the page results along with pagination metadata
        cache_data = {
            "results": results,
            "count": total_count,
        }
        cache.set(cache_key, cache_data, self.cache_timeout)

        # Set instance attributes
        self.count = total_count
        # results.count = total_count  # Attach count to results for consistency
        return results

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
        return f"combined-page-cache:{cache_hash}"

    def get_paginated_response(self, data):
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
                "count": getattr(self, "count", None),  # Include count if available
            }
        )

    # def get_next_link(self):
    #     if not getattr(self, "has_next", False):
    #         return None

    #     url = self.request.build_absolute_uri()
    #     offset = self.offset + self.limit
    #     return replace_query_param(url, self.offset_query_param, offset)

    # def get_previous_link(self):
    #     if not getattr(self, "has_previous", False):
    #         return None

    #     url = self.request.build_absolute_uri()
    #     offset = self.offset - self.limit
    #     if offset <= 0:
    #         return remove_query_param(url, self.offset_query_param)
    #     return replace_query_param(url, self.offset_query_param, offset)
