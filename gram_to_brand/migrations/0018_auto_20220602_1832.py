# Generated by Django 2.2 on 2022-06-02 18:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0017_auto_20220602_1725'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='grnorderproductmapping',
            name='barcode_id',
        ),
        migrations.RemoveField(
            model_name='grnorderproductmapping',
            name='product_invoice_gst',
        ),
    ]
