# Generated by Django 2.2 on 2022-06-17 15:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wms', '0004_binshiftlog'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='qcdesk',
            name='desk_type',
        ),
        migrations.DeleteModel(
            name='BinShiftLog',
        ),
    ]
