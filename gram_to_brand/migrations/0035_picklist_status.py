# Generated by Django 2.1 on 2018-12-01 01:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0034_auto_20181201_0031'),
    ]

    operations = [
        migrations.AddField(
            model_name='picklist',
            name='status',
            field=models.BooleanField(default=False),
        ),
    ]