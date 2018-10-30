# Generated by Django 2.1 on 2018-10-25 18:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_productpricecsv_area'),
        ('sp_to_gram', '0005_auto_20181023_1637'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderedProductReserved',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reserved_qty', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('cart', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_ordered_retailer_cart', to='sp_to_gram.Cart')),
                ('ordered_product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_order_product_order_product_reserved', to='sp_to_gram.OrderedProduct')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_product_order_product_reserved', to='products.Product')),
            ],
        ),
        migrations.AddField(
            model_name='orderedproductmapping',
            name='expiry_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='orderedproductmapping',
            name='manufacture_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]