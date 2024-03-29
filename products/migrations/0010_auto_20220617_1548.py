# Generated by Django 2.2 on 2022-06-17 15:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_auto_20220602_1153'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='superstoreproductpricelog',
            name='product_price_change',
        ),
        migrations.RemoveField(
            model_name='superstoreproductpricelog',
            name='updated_by',
        ),
        migrations.AlterField(
            model_name='parentproduct',
            name='product_type',
            field=models.CharField(choices=[('b2b', 'B2B'), ('b2c', 'B2C'), ('both', 'Both B2B and B2C')], default='both', max_length=5),
        ),
        migrations.AlterField(
            model_name='parentproducttaxapprovallog',
            name='parent_product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='parent_product_tax_approval_log', to='products.ParentProduct'),
        ),
        migrations.DeleteModel(
            name='SuperStoreProductPrice',
        ),
        migrations.DeleteModel(
            name='SuperStoreProductPriceLog',
        ),
    ]
