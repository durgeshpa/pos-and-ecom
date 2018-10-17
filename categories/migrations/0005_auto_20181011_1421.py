# Generated by Django 2.1 on 2018-10-11 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0004_auto_20181010_1722'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='category_name',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='category',
            name='category_sku_part',
            field=models.CharField(help_text='Please enter two character for SKU', max_length=2, unique=True),
        ),
        migrations.AlterField(
            model_name='category',
            name='category_slug',
            field=models.SlugField(unique=True),
        ),
    ]