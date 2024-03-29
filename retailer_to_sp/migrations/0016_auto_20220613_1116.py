# Generated by Django 2.2 on 2022-06-13 11:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_auto_20220602_1153'),
        ('accounts', '0001_initial'),
        ('pos', '0035_auto_20220610_1224'),
        ('shops', '0018_shop_shop_code_super_store'),
        ('retailer_to_sp', '0015_orderedproduct_shipment_label_pdf'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReturnOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('return_no', models.CharField(blank=True, max_length=255, null=True)),
                ('return_status', models.CharField(blank=True, choices=[('RETURN_REQUESTED', 'Return requested'), ('RETURN_INITIATED', 'Return initiated'), ('CUSTOMER_ITEM_PICKED', 'Customer item picked'), ('STORE_ITEM_PICKED', 'Retailer Item Picked'), ('DC_DROPPED', 'DC Dropped'), ('WH_DROPPED', 'WH Dropped'), ('RETURN_CANCEL', 'Return cancelled')], max_length=50, null=True, verbose_name='Status for Return')),
                ('return_reason', models.CharField(blank=True, choices=[('defective_damaged_item', 'Defective / Damaged item'), ('wrong_item_delivered', 'Wrong item delivered'), ('item_did_not_match_description', 'Item did not match description'), ('other', 'other reason')], max_length=50, null=True, verbose_name='Reason for Return')),
                ('return_pickup_method', models.CharField(blank=True, choices=[('DROP_AT_STORE', 'Drop at Store'), ('HOME_PICKUP', 'Home Pickup')], max_length=50, null=True, verbose_name='Method for Product pick up')),
                ('other_return_reason', models.CharField(blank=True, max_length=100, null=True, verbose_name='Verbose return reason')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('buyer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='buyer_return_orders', to='accounts.User')),
                ('buyer_shop', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='buyer_shop_return_orders', to='shops.Shop')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='last_modified_return_order', to='accounts.User')),
                ('return_item_pickup_person', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='return_item_pickups', to='accounts.UserWithName', verbose_name='Return Item Pick up')),
                ('seller_shop', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='seller_shop_return_orders', to='shops.Shop')),
            ],
            options={
                'verbose_name': 'Return Order request',
                'verbose_name_plural': 'Return Order requests',
            },
        ),
        migrations.CreateModel(
            name='ReturnOrderProduct',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('return_qty', models.PositiveIntegerField(default=0, verbose_name='Returned Quantity')),
                ('return_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('last_modified_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='modified_by_return_orders', to='accounts.User')),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='return_order_products', to='products.Product')),
                ('retailer_product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='return_order_retailer_products', to='pos.RetailerProduct')),
                ('return_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_order_products', to='retailer_to_sp.ReturnOrder')),
            ],
            options={
                'verbose_name': 'Return Order Product',
                'verbose_name_plural': 'Return Order Products',
            },
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='is_returned',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='ReturnOrderProductImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('return_image', models.FileField(upload_to='return_photos/documents/')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('return_order_product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_order_product_images', to='retailer_to_sp.ReturnOrderProduct')),
            ],
            options={
                'verbose_name': 'Return Order Product Image',
                'verbose_name_plural': 'Return Order Product Images',
            },
        ),
        migrations.AddField(
            model_name='returnorder',
            name='shipment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shipment_return_orders', to='retailer_to_sp.OrderedProduct'),
        ),
    ]
