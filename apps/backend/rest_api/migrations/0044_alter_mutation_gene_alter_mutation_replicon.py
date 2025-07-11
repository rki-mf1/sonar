# Generated by Django 4.2.8 on 2023-12-26 11:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rest_api', '0043_alter_alignment_replicon_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mutation',
            name='gene',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rest_api.gene'),
        ),
        migrations.AlterField(
            model_name='mutation',
            name='replicon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rest_api.replicon'),
        ),
    ]
