from rest_api import viewsets
from rest_api import viewsets_database
from rest_api import viewsets_sample
from rest_framework import routers

router = routers.SimpleRouter()
router.register(r"mutations", viewsets.MutationViewSet, basename="mutation")
router.register(r"snp1", viewsets.SNP1ViewSet, basename="snp1")
router.register(
    r"mutation_signatures",
    viewsets.MutationSignatureViewSet,
    basename="mutation_signature",
)
router.register(r"samples", viewsets_sample.SampleViewSet, basename="sample")
router.register(
    r"sample_genomes", viewsets_sample.SampleGenomeViewSet, basename="sample_genome"
)
router.register(r"references", viewsets.ReferenceViewSet, basename="reference")
router.register(r"replicons", viewsets.RepliconViewSet, basename="replicon")
router.register(r"alignments", viewsets.AlignmentViewSet, basename="alignment")
router.register(r"properties", viewsets.PropertyViewSet, basename="property")
router.register(r"aa_mutations", viewsets.AAMutationViewSet, basename="aa_mutation")
router.register(r"genes", viewsets.GeneViewSet, basename="gene")
router.register(r"resources", viewsets.ResourceViewSet, basename="resources")
router.register(r"file_uploads", viewsets.FileUploadViewSet, basename="import_upload")
router.register(r"lineages", viewsets.LineageViewSet, basename="lineage")
router.register(r"tasks", viewsets.TasksView, basename="tasks")
router.register(r"database", viewsets_database.DatabaseInfoView, basename="database")

urlpatterns = [*router.urls]
