# Generated by Django 2.1 on 2018-11-01 12:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('retailer_to_sp', '0008_auto_20181101_1130'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='note',
            unique_together={('order', 'ordered_product')},
        ),
    ]
