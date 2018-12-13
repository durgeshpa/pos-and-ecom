# Generated by Django 2.1 on 2018-12-05 16:42

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0027_auto_20181204_1723'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductSKUGenerator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parent_cat_sku_code', models.CharField(help_text='Please enter three characters for SKU', max_length=3, unique=True, validators=[django.core.validators.RegexValidator('^[A-Z]{3}$', 'Only three capital alphates allowed')])),
                ('cat_sku_code', models.CharField(help_text='Please enter three characters for SKU', max_length=3, unique=True, validators=[django.core.validators.RegexValidator('^[A-Z]{3}$', 'Only three capital alphates allowed')])),
                ('brand_sku_code', models.CharField(help_text='Please enter three characters for SKU', max_length=3, unique=True, validators=[django.core.validators.RegexValidator('^[A-Z]{3}$', 'Only three capital alphates allowed')])),
                ('last_auto_increment', models.PositiveIntegerField()),
            ],
        ),
    ]
