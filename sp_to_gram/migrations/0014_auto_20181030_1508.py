# Generated by Django 2.1 on 2018-10-30 15:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sp_to_gram', '0013_auto_20181030_1459'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderedproductreserved',
            name='ordered_product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sp_order_product_order_product_reserved', to='sp_to_gram.OrderedProductMapping'),
        ),
    ]
