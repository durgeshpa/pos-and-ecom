# Generated by Django 2.1 on 2018-12-13 17:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0017_auto_20181204_1612'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='parentretailermapping',
            unique_together={('parent', 'retailer')},
        ),
    ]
