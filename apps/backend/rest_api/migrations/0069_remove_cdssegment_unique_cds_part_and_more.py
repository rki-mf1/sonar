# Generated by Django 5.1.7 on 2025-03-24 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rest_api", "0068_cds_cdssegment_peptide_peptidesegment_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="cdssegment",
            name="unique_cds_part",
        ),
        migrations.RemoveConstraint(
            model_name="peptidesegment",
            name="unique_peptide_part",
        ),
        migrations.AddField(
            model_name="gene",
            name="locus_tag",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddConstraint(
            model_name="cdssegment",
            constraint=models.UniqueConstraint(
                fields=("cds", "order"), name="unique_cds_segment"
            ),
        ),
        migrations.AddConstraint(
            model_name="peptidesegment",
            constraint=models.UniqueConstraint(
                fields=("peptide", "order"), name="unique_peptide_segment"
            ),
        ),
        migrations.AlterModelTable(
            name="cdssegment",
            table="cds_segment",
        ),
        migrations.AlterModelTable(
            name="peptidesegment",
            table="peptide_segement",
        ),
    ]
