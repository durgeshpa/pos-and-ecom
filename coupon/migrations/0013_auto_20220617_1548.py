# Generated by Django 2.2 on 2022-06-17 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon', '0012_auto_20220617_1049'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupon',
            name='coupon_enable_on',
        ),
        migrations.RemoveField(
            model_name='coupon',
            name='coupon_shop_type',
        ),
        migrations.RemoveField(
            model_name='coupon',
            name='limit_of_usages_per_customer',
        ),
        migrations.RemoveField(
            model_name='discountvalue',
            name='is_point',
        ),
        migrations.AlterField(
            model_name='couponruleset',
            name='no_of_users_allowed',
            field=models.ManyToManyField(blank=True, to='accounts.User'),
        ),
    ]