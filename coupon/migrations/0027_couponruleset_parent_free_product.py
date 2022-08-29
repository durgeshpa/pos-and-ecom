# Generated by Django 2.2 on 2022-06-24 11:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_auto_20220617_1613'),
        ('coupon', '0026_auto_20220623_1306'),
    ]

    operations = [
        migrations.AddField(
            model_name='couponruleset',
            name='parent_free_product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='parent_free_product', to='products.Product'),
        ),
    ]
