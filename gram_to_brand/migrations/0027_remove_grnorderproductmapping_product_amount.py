# Generated by Django 2.2 on 2022-06-02 18:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0026_grnorderproductmapping_cess_percentage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='grnorderproductmapping',
            name='product_amount',
        ),
    ]
