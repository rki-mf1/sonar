# Generated by Django 4.2.8 on 2024-01-25 04:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rest_api', '0047_alter_sample2property_value_float'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lineage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prefixed_alias', models.CharField(blank=True, max_length=50, null=True)),
                ('lineage', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'lineage',
            },
        ),
        migrations.CreateModel(
            name='LineageAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alias', models.CharField(max_length=50)),
                ('parent_alias', models.CharField(blank=True, max_length=50, null=True)),
                ('lineage', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rest_api.lineage')),
            ],
            options={
                'db_table': 'lineage_alias',
            },
        ),
        migrations.DeleteModel(
            name='Lineages',
        ),
        migrations.AddConstraint(
            model_name='lineage',
            constraint=models.UniqueConstraint(fields=('prefixed_alias', 'lineage'), name='unique_lineage'),
        ),
        migrations.AddConstraint(
            model_name='lineage',
            constraint=models.UniqueConstraint(condition=models.Q(('prefixed_alias__isnull', True)), fields=('lineage',), name='unique_lineage_null_alias'),
        ),
        migrations.AddConstraint(
            model_name='lineagealias',
            constraint=models.UniqueConstraint(condition=models.Q(('parent_alias__isnull', True)), fields=('alias', 'lineage'), name='unique_alias2lineage'),
        ),
        migrations.AddConstraint(
            model_name='lineagealias',
            constraint=models.UniqueConstraint(condition=models.Q(('lineage__isnull', True)), fields=('alias', 'parent_alias'), name='unique_alias2parent_alias'),
        ),
    ]
