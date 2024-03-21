from django.contrib import admin

# Register your models here.
from rest_api import models

admin.site.register(models.Sequence)
admin.site.register(models.Alignment)
admin.site.register(models.Alignment2Mutation)
admin.site.register(models.AnnotationType)
admin.site.register(models.Replicon)
admin.site.register(models.Gene)
admin.site.register(models.GeneSegment)
admin.site.register(models.Lineage)
admin.site.register(models.LineageAlias)
admin.site.register(models.Reference)
admin.site.register(models.Property)
admin.site.register(models.Sample)
admin.site.register(models.Sample2Property)
admin.site.register(models.Mutation)
admin.site.register(models.Mutation2Annotation)
admin.site.register(models.ImportLog)