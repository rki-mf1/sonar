from django.urls import path, include
from rest_framework import routers, serializers, viewsets
from rest_api import viewsets
from django.contrib import admin
from . import settings
import pprint

router = routers.DefaultRouter()
router.register(r"mutations", viewsets.MutationViewSet)
router.register(r"snp1", viewsets.SNP1ViewSet)
router.register(r"mutation_signature", viewsets.MutationSignatureViewSet)
router.register(r"samples", viewsets.SampleViewSet)
router.register(r"sample_genomes", viewsets.SampleGenomeViewSet)
router.register(r"references", viewsets.ReferenceViewSet)
router.register(r"replicons", viewsets.RepliconViewSet)
router.register(r"alignments", viewsets.AlignmentViewSet)
router.register(r"property", viewsets.PropertyViewSet)
router.register(r"aa_mutations", viewsets.AAMutationViewSet)
router.register(r"genes", viewsets.GeneViewSet)
router.register(r'resources', viewsets.ResourceViewSet, basename='resources')
router.register(r'file_uploads', viewsets.FileUploadViewSet, basename='import_upload')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(router.urls)),
    # path('alignments/get_alignment_data/<int:seq_id>/<int:element_id>/', viewsets.AlignmentViewSet.as_view({'get': 'get_alignment_data'}), name='get_alignment_data'),
]

pprint.pprint(router.urls)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),

    ]