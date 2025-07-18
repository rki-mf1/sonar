# Generated by Django 4.2.4 on 2023-11-03 12:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("rest_api", "0027_mutation_mutation_type_bf4ac1_idx"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="mutation",
            name="mutation_label_94967f_idx",
        ),
        migrations.RemoveField(
            model_name="mutation",
            name="frameshift",
        ),
        migrations.RemoveField(
            model_name="mutation",
            name="label",
        ),
        migrations.AddField(
            model_name="gene",
            name="cds_accession",
            field=models.CharField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="gene",
            name="cds_symbol",
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="mutation",
            name="replicon",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="rest_api.replicon",
            ),
        ),
        migrations.AddField(
            model_name="reference",
            name="name",
            field=models.CharField(blank=True, null=True, unique=True),
        ),
    ]
