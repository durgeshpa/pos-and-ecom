# Generated by Django 2.1 on 2018-10-15 11:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0004_auto_20181015_1141'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cartproductmapping',
            old_name='cart_price',
            new_name='price',
        ),
    ]