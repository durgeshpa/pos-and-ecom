# Generated by Django 2.1 on 2018-10-15 12:09

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0007_auto_20181015_1201'),
    ]

    operations = [
        migrations.AddField(
            model_name='carordershipmentmapping',
            name='batch_no',
            field=models.CharField(default=django.utils.timezone.now, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='ordershipment',
            name='car_order_shipment_mapping',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='car_order_shipment_mapping_shipment', to='gram_to_brand.CarOrderShipmentMapping'),
        ),
        migrations.AlterField(
            model_name='ordershipment',
            name='cart_product_ship',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cart_product_mapping_shipment', to='gram_to_brand.CartProductMapping'),
        ),
    ]