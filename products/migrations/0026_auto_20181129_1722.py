# Generated by Django 2.1 on 2018-11-29 17:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0025_auto_20181129_1625'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='product_case_size',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='product',
            name='product_inner_case_size',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
