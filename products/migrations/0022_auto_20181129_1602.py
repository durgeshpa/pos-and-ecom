# Generated by Django 2.1 on 2018-11-29 16:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0021_auto_20181129_1555'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productsurcharge',
            name='product',
        ),
        migrations.DeleteModel(
            name='ProductSurcharge',
        ),
    ]
