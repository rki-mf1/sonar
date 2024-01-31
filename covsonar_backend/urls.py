from django.urls import path, include
from django.contrib import admin
from . import settings


urlpatterns = [
    path("admin/", admin.site.urls, name="admin"),
    path("api/", include("rest_api.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls), name="debug_toolbar"),
    ]
