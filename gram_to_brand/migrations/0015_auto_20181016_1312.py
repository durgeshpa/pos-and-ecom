# Generated by Django 2.1 on 2018-10-16 13:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0014_orderitem_ordered_product_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderitem',
            old_name='damaged_sum_qty',
            new_name='damaged_total_qty',
        ),
        migrations.RenameField(
            model_name='orderitem',
            old_name='delivered_sum_qty',
            new_name='delivered_total_qty',
        ),
        migrations.RenameField(
            model_name='orderitem',
            old_name='returned_sum_qty',
            new_name='returned_total_qty',
        ),
    ]
