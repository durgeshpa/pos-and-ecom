# Generated by Django 2.1 on 2018-10-30 15:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sp_to_gram', '0014_auto_20181030_1508'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderedproductreserved',
            old_name='ordered_product',
            new_name='order_product_reserved',
        ),
    ]
