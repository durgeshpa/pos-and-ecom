# Generated by Django 2.1 on 2022-04-04 16:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gram_to_brand', '0001_initial'),
        ('shops', '0001_initial'),
        ('brand', '0001_initial'),
        ('retailer_to_sp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoOrderProcessing',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('state', models.PositiveSmallIntegerField(choices=[(0, 'GRN Done'), (1, 'Putaway Done'), (2, 'Cart Created'), (3, 'Cart Reserved'), (4, 'Order Placed'), (5, 'Pickup Created'), (6, 'Picking Assigned'), (7, 'Pickup Completed'), (8, 'Shipment Created'), (9, 'QC Done'), (10, 'Trip Created'), (11, 'Trip Started'), (12, 'Delivered'), (13, 'PO Created'), (14, 'AUTO GRN Done')], default=1)),
                ('auto_grn', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auto_processing_by_grn', to='gram_to_brand.GRNOrder')),
                ('auto_po', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='grn_for_po', to='gram_to_brand.Cart')),
                ('cart', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auto_processing_carts', to='retailer_to_sp.Cart')),
                ('grn', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='auto_order', to='gram_to_brand.GRNOrder')),
                ('grn_warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_grns_for_auto_processing', to='shops.Shop')),
                ('order', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auto_processing_orders', to='retailer_to_sp.Order')),
                ('retailer_shop', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auto_processing_shop_entries', to='shops.Shop')),
                ('source_po', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auto_process_entries_for_po', to='gram_to_brand.Cart')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SourceDestinationMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('dest_wh', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='shops.Shop', unique=True)),
                ('retailer_shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='shops.Shop')),
                ('source_wh', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='shops.Shop', unique=True)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='brand.Vendor')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]