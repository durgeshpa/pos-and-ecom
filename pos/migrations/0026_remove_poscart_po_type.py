# Generated by Django 2.2 on 2022-06-02 15:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0025_auto_20220602_1153'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='poscart',
            name='po_type',
        ),
    ]
