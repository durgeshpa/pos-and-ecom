# Generated by Django 2.2 on 2022-06-10 12:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coupon', '0006_coupon_limit_of_usages_per_customer'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupon',
            name='limit_of_usages_per_customer',
        ),
    ]