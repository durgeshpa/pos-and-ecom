# Generated by Django 2.1 on 2018-11-01 16:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('retailer_to_sp', '0010_order_payment_status'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='note',
            unique_together=set(),
        ),
    ]
