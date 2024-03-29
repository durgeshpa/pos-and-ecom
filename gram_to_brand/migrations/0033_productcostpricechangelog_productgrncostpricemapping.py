# Generated by Django 2.2 on 2022-07-27 17:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_parentproduct_is_kvi'),
        ('gram_to_brand', '0032_auto_20220610_1224'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductGRNCostPriceMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('current_inv', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('latest_grn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_cost_grn_mappings', to='gram_to_brand.GRNOrderProductMapping')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cost_price', to='products.Product')),
            ],
            options={
                'verbose_name': 'Product GRN Cost Price mapping',
                'verbose_name_plural': 'Product Cost Prices mapping',
            },
        ),
        migrations.CreateModel(
            name='ProductCostPriceChangeLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('current_inv', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cost_price_grn_mapping', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cost_price_change_logs', to='gram_to_brand.ProductGRNCostPriceMapping')),
                ('grn', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cost_price_change_logs', to='gram_to_brand.GRNOrderProductMapping')),
            ],
            options={
                'verbose_name': 'Product Cost Price change log',
                'verbose_name_plural': 'Product Cost Price change logs',
            },
        ),
    ]
