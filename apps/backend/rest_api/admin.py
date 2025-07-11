from django.contrib import admin

from rest_api import models

# Register your models here.

admin.site.register(models.Sequence)
admin.site.register(models.Alignment)
admin.site.register(models.AnnotationType)
admin.site.register(models.Replicon)
admin.site.register(models.Gene)
admin.site.register(models.GeneSegment)
admin.site.register(models.Lineage)
admin.site.register(models.Reference)
admin.site.register(models.Property)
admin.site.register(models.Sample)
admin.site.register(models.Sample2Property)
admin.site.register(models.NucleotideMutation)
admin.site.register(models.AminoAcidMutation)
admin.site.register(models.ImportLog)
admin.site.register(models.FileProcessing)
admin.site.register(models.ProcessingJob)
