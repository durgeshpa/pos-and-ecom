# Generated by Django 2.1 on 2022-04-18 13:35

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0004_auto_20220417_2010'),
    ]

    operations = [
        migrations.AddField(
            model_name='functions',
            name='required_headers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, null=True, size=None),
        ),
        migrations.AlterField(
            model_name='carditem',
            name='content_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
