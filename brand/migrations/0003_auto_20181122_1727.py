# Generated by Django 2.1 on 2018-11-22 17:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('brand', '0002_auto_20181122_1726'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='brand',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='brand',
            name='brand_slug',
        ),
    ]
