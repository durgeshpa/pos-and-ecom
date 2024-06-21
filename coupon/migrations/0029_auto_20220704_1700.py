# Generated by Django 2.2 on 2022-07-04 17:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon', '0028_coupon_coupon_type_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupon',
            name='category',
        ),
        migrations.RemoveField(
            model_name='coupon',
            name='coupon_type_name',
        ),
        migrations.RemoveField(
            model_name='coupon',
            name='froms',
        ),
        migrations.RemoveField(
            model_name='coupon',
            name='is_admin',
        ),
        migrations.RemoveField(
            model_name='coupon',
            name='to',
        ),
        migrations.RemoveField(
            model_name='couponruleset',
            name='parent_free_product',
        ),
        migrations.AlterField(
            model_name='coupon',
            name='coupon_shop_type',
            field=models.CharField(blank=True, choices=[('all', 'All'), ('fofo', 'Fofo'), ('foco', 'Foco')], max_length=20, null=True),
        ),
    ]