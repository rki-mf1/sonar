# Generated by Django 4.2.4 on 2023-10-05 10:10

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "rest_api",
            "0015_gene_genepart_sourceelement_remove_element_molecule_and_more",
        ),
    ]

    operations = [
        migrations.AlterModelTable(
            name="gene",
            table="gene",
        ),
    ]
