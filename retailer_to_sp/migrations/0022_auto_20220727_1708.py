# Generated by Django 2.2 on 2022-07-27 17:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coupon', '0030_auto_20220706_1553'),
        ('brand', '0002_auto_20220404_1624'),
        ('products', '0012_parentproduct_is_kvi'),
        ('retailer_to_sp', '0021_auto_20220706_1553'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='cart_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='cartproductmapping',
            name='cost_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='orderedproductmapping',
            name='cost_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.CreateModel(
            name='CartOffers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('FREE', 'free'), ('DISCOUNT', 'discount'), ('NO_OFFER', 'no offer')], max_length=20)),
                ('sub_type', models.CharField(choices=[('NONE', 'none'), ('DISCOUNT_ON_BRAND', 'disount_on_brand'), ('DISCOUNT_ON_CART', 'discount_on_cart'), ('DISCOUNT_ON_PRODUCT', 'discount_on_product')], max_length=20)),
                ('sub_total', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('discount', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('free_product_qty', models.SmallIntegerField(null=True)),
                ('cart_discount', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('brand_discount', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('entice_text', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('brand', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='brand_offers', to='brand.Brand')),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_offers', to='retailer_to_sp.Cart')),
                ('cart_item', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='item_offers', to='retailer_to_sp.CartProductMapping')),
                ('coupon', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='coupon_carts', to='coupon.Coupon')),
                ('free_product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='pro_coupon_carts', to='products.Product')),
            ],
        ),
    ]
