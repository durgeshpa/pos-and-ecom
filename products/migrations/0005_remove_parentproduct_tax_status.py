# Generated by Django 2.1 on 2022-04-06 21:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_auto_20220406_2012'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='parentproduct',
            name='tax_status',
        ),
    ]
