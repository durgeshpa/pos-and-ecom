# Generated by Django 2.2 on 2022-06-02 18:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0022_remove_grnorderproductmapping_barcode_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='grnorderproductmapping',
            name='product_invoice_gst',
        ),
    ]
