# Generated by Django 5.1.4 on 2024-12-19 12:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "rest_api",
            "0066_remove_nucleotidemutation_unique_nt_mutation_null_alt_and_more",
        ),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="aminoacidmutation",
            name="unique_aa_mutation_null_gene",
        ),
        migrations.RemoveConstraint(
            model_name="aminoacidmutation",
            name="unique_aa_mutation_null_alt",
        ),
        migrations.RemoveConstraint(
            model_name="aminoacidmutation",
            name="unique_aa_mutation_null_ref",
        ),
        migrations.RemoveConstraint(
            model_name="aminoacidmutation",
            name="unique_aa_mutation_null_alt_null_gene",
        ),
        migrations.AlterField(
            model_name="aminoacidmutation",
            name="alt",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="aminoacidmutation",
            name="end",
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name="aminoacidmutation",
            name="gene",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="rest_api.gene"
            ),
        ),
        migrations.AlterField(
            model_name="aminoacidmutation",
            name="ref",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="aminoacidmutation",
            name="replicon",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="rest_api.replicon"
            ),
        ),
        migrations.AlterField(
            model_name="aminoacidmutation",
            name="start",
            field=models.BigIntegerField(),
        ),
    ]
