# Generated by Django 2.1 on 2022-04-04 16:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wms', '0001_initial'),
        ('shops', '0001_initial'),
        ('products', '0002_auto_20220404_1624'),
        ('pos', '0002_auto_20220404_1624'),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='warehouseinventoryhistoric',
            name='inventory_state',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='wms.InventoryState'),
        ),
        migrations.AddField(
            model_name='warehouseinventoryhistoric',
            name='inventory_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='wms.InventoryType'),
        ),
        migrations.AddField(
            model_name='warehouseinventoryhistoric',
            name='sku',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='products.Product', to_field='product_sku'),
        ),
        migrations.AddField(
            model_name='warehouseinventoryhistoric',
            name='warehouse',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='posinventoryhistoric',
            name='inventory_state',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='wms.PosInventoryState'),
        ),
        migrations.AddField(
            model_name='posinventoryhistoric',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='pos.RetailerProduct'),
        ),
        migrations.AddField(
            model_name='bininventoryhistoric',
            name='archive_entry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='services.InventoryArchiveMaster'),
        ),
        migrations.AddField(
            model_name='bininventoryhistoric',
            name='bin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='wms.Bin'),
        ),
        migrations.AddField(
            model_name='bininventoryhistoric',
            name='inventory_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='wms.InventoryType'),
        ),
        migrations.AddField(
            model_name='bininventoryhistoric',
            name='sku',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='products.Product', to_field='product_sku'),
        ),
        migrations.AddField(
            model_name='bininventoryhistoric',
            name='warehouse',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='shops.Shop'),
        ),
    ]
