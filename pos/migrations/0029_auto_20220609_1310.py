# Generated by Django 2.2 on 2022-06-09 13:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0028_auto_20220609_1307'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='postrip',
            name='shipment',
        ),
        migrations.RemoveField(
            model_name='postrip',
            name='trip_end_at',
        ),
        migrations.RemoveField(
            model_name='postrip',
            name='trip_start_at',
        ),
        migrations.RemoveField(
            model_name='postrip',
            name='trip_type',
        ),
    ]
