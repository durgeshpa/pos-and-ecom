# Generated by Django 2.2 on 2022-06-17 15:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0018_shop_shop_code_super_store'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shop',
            name='shop_code_super_store',
        ),
        migrations.RemoveField(
            model_name='shop',
            name='superstore_enable',
        ),
    ]
