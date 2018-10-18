# Generated by Django 2.1 on 2018-10-17 14:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('shops', '0002_auto_20181008_1319'),
        ('products', '0004_auto_20181016_1227'),
        ('accounts', '0001_initial'),
        ('addresses', '0002_auto_20181008_1319'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.CharField(blank=True, max_length=255, null=True)),
                ('cart_status', models.CharField(blank=True, choices=[('ordered_to_brand', 'Ordered To Brand'), ('partially_delivered', 'Partially Delivered'), ('delivered', 'Delivered')], max_length=200, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_last_modified_user_cart', to='accounts.User')),
                ('shop', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_shop_cart', to='shops.Shop')),
            ],
        ),
        migrations.CreateModel(
            name='CartProductMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty', models.PositiveIntegerField(default=0)),
                ('price', models.FloatField(default=0)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sp_cart_list', to='sp_to_gram.Cart')),
                ('cart_product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sp_cart_product_mapping', to='products.Product')),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_no', models.CharField(blank=True, max_length=255, null=True)),
                ('total_mrp', models.FloatField(default=0)),
                ('total_discount_amount', models.FloatField(default=0)),
                ('total_tax_amount', models.FloatField(default=0)),
                ('total_final_amount', models.FloatField(default=0)),
                ('order_status', models.CharField(choices=[('ordered_to_brand', 'Ordered To Brand'), ('partially_delivered', 'Partially Delivered'), ('delivered', 'Delivered')], max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('billing_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_billing_address_order', to='addresses.Address')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_brand_order_modified_user', to='accounts.User')),
                ('ordered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_brand_order_by_user', to='accounts.User')),
                ('ordered_cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sp_order_cart_mapping', to='sp_to_gram.Cart')),
                ('received_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_brand_received_by_user', to='accounts.User')),
                ('shipping_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_shipping_address_order', to='addresses.Address')),
                ('shop', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_shop_order', to='shops.Shop')),
            ],
        ),
    ]
