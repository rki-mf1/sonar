from django.urls import path, include
from rest_framework import routers, serializers, viewsets
from rest_api import viewsets
from django.contrib import admin
from . import settings

router = routers.DefaultRouter()
router.register(r"mutations", viewsets.MutationViewSet)
router.register(r"snp1", viewsets.SNP1ViewSet)
router.register(r"mutation_signature", viewsets.MutationSignatureViewSet)
router.register(r"samples", viewsets.SampleViewSet)
router.register(r"sample_genomes", viewsets.SampleGenomeViewSet)
router.register(r"references", viewsets.ReferenceViewSet)
router.register(r"property", viewsets.PropertyViewSet)
router.register(r"aa_mutations", viewsets.AAMutationViewSet)
router.register(r"gene", viewsets.GeneViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(router.urls)),
]
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]