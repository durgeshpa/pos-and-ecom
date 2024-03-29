# Generated by Django 2.2 on 2022-06-17 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('retailer_to_sp', '0017_auto_20220617_1049'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='returnorderproduct',
            name='last_modified_by',
        ),
        migrations.RemoveField(
            model_name='returnorderproduct',
            name='product',
        ),
        migrations.RemoveField(
            model_name='returnorderproduct',
            name='retailer_product',
        ),
        migrations.RemoveField(
            model_name='returnorderproduct',
            name='return_order',
        ),
        migrations.RemoveField(
            model_name='returnorderproductimage',
            name='return_order_product',
        ),
        migrations.RemoveField(
            model_name='order',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='order',
            name='longitude',
        ),
        migrations.RemoveField(
            model_name='order',
            name='reference_order',
        ),
        migrations.RemoveField(
            model_name='orderedproduct',
            name='delivery_person',
        ),
        migrations.RemoveField(
            model_name='orderedproduct',
            name='is_returned',
        ),
        migrations.RemoveField(
            model_name='orderedproduct',
            name='points_added',
        ),
        migrations.RemoveField(
            model_name='orderedproduct',
            name='shipment_label_pdf',
        ),
        migrations.AlterField(
            model_name='cart',
            name='cart_type',
            field=models.CharField(choices=[('RETAIL', 'Retail'), ('BULK', 'Bulk'), ('DISCOUNTED', 'Discounted'), ('BASIC', 'Basic'), ('EC0M', 'Ecom')], default='RETAIL', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_app_type',
            field=models.CharField(blank=True, choices=[('pos_walkin', 'Pos Walkin'), ('pos_ecomm', 'Pos Ecomm')], max_length=50, null=True),
        ),
        migrations.DeleteModel(
            name='ReturnOrder',
        ),
        migrations.DeleteModel(
            name='ReturnOrderProduct',
        ),
        migrations.DeleteModel(
            name='ReturnOrderProductImage',
        ),
    ]
