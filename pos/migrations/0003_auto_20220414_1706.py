# Generated by Django 2.1 on 2022-04-14 17:06

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0006_auto_20220414_1706'),
        ('pos', '0002_auto_20220404_1624'),
    ]

    operations = [
        migrations.CreateModel(
            name='PosStoreRewardMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True)),
                ('min_order_value', models.DecimalField(blank=True, decimal_places=2, default=199, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(199)])),
                ('point_add_pos_order', models.IntegerField(blank=True, null=True)),
                ('point_add_ecom_order', models.IntegerField(blank=True, null=True)),
                ('max_redeem_point_ecom', models.IntegerField(blank=True, null=True)),
                ('max_redeem_point_pos', models.IntegerField(blank=True, null=True)),
                ('value_of_each_point', models.DecimalField(blank=True, decimal_places=2, default=199, max_digits=10, null=True)),
                ('first_order_redeem_point', models.IntegerField(blank=True, null=True)),
                ('second_order_redeem_point', models.IntegerField(blank=True, null=True)),
                ('max_monthly_points_added', models.IntegerField(blank=True, null=True)),
                ('max_monthly_points_redeemed', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shops.Shop', unique=True)),
            ],
            options={
                'verbose_name': 'POS Store Reward Mapping',
            },
        ),
        migrations.AlterField(
            model_name='productchangefields',
            name='column_name',
            field=models.CharField(choices=[('selling_price', 'Selling Price'), ('mrp', 'MRP'), ('offer_price', 'offer_price'), ('offer_start_date', 'Offer Start Date'), ('offer_end_date', 'Offer End Date'), ('linked_product_id', 'Linked Product')], max_length=255),
        ),
    ]