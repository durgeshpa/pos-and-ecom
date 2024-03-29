# Generated by Django 2.2 on 2022-06-17 16:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_auto_20220617_1613'),
        ('accounts', '0001_initial'),
        ('shops', '0020_auto_20220617_1613'),
        ('wms', '0005_auto_20220617_1548'),
    ]

    operations = [
        migrations.AddField(
            model_name='qcdesk',
            name='desk_type',
            field=models.CharField(choices=[('GROCERY', 'Grocery'), ('SUPERSTORE', 'Super Store')], default='GROCERY', max_length=15, null=True),
        ),
        migrations.CreateModel(
            name='BinShiftLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_id', models.CharField(max_length=50)),
                ('qty', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='accounts.User', verbose_name='Created by')),
                ('inventory_type', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='wms.InventoryType')),
                ('s_bin', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='wms.Bin', verbose_name='Source Bin')),
                ('sku', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='products.Product', to_field='product_sku')),
                ('t_bin', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='wms.Bin', verbose_name='Target Bin')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='shops.Shop')),
            ],
        ),
    ]
