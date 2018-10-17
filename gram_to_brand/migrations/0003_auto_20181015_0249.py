# Generated by Django 2.1 on 2018-10-15 02:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0002_carordershipmentmapping_cart'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='ordered_shipment',
            field=models.ManyToManyField(limit_choices_to={'car_order_shipment': 3}, related_name='order_shipment_mapping', to='gram_to_brand.CarOrderShipmentMapping'),
        ),
    ]