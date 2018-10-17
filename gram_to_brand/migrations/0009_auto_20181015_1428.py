# Generated by Django 2.1 on 2018-10-15 14:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_auto_20181008_1319'),
        ('gram_to_brand', '0008_auto_20181015_1209'),
    ]

    operations = [
        migrations.CreateModel(
            name='GRNOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_no', models.CharField(max_length=255)),
                ('grn_id', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='GRNOrderProductMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changed_price', models.FloatField(default=0)),
                ('manufacture_date', models.DateField(blank=True, null=True)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('delivered_qty', models.PositiveIntegerField(default=0)),
                ('returned_qty', models.PositiveIntegerField(default=0)),
                ('damaged_qty', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_grn_order_product', to='products.Product')),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordered_qty', models.PositiveIntegerField(default=0)),
                ('ordered_price', models.FloatField(default=0)),
                ('item_status', models.CharField(choices=[('partially_delivered', 'Partially Delivered'), ('delivered', 'Delivered')], max_length=255)),
                ('delivered_sum_qty', models.PositiveIntegerField(default=0)),
                ('returned_sum_qty', models.PositiveIntegerField(default=0)),
                ('damaged_sum_qty', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.RemoveField(
            model_name='carordershipmentmapping',
            name='cart',
        ),
        migrations.RemoveField(
            model_name='ordershipment',
            name='car_order_shipment_mapping',
        ),
        migrations.RemoveField(
            model_name='ordershipment',
            name='cart_product_ship',
        ),
        migrations.RemoveField(
            model_name='ordershipment',
            name='cart_products',
        ),
        migrations.RemoveField(
            model_name='order',
            name='ordered_shipment',
        ),
        migrations.DeleteModel(
            name='CarOrderShipmentMapping',
        ),
        migrations.DeleteModel(
            name='OrderShipment',
        ),
        migrations.AddField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_order_item', to='gram_to_brand.Order'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='ordered_product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_order_item', to='products.Product'),
        ),
        migrations.AddField(
            model_name='grnorder',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_grn_order', to='gram_to_brand.Order'),
        ),
        migrations.AddField(
            model_name='grnorder',
            name='order_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_item_grn_order', to='gram_to_brand.OrderItem'),
        ),
    ]
