# Generated by Django 2.1 on 2018-11-29 12:00

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_auto_20181110_1927'),
    ]

    operations = [
        migrations.AlterField(
            model_name='color',
            name='color_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_PRODUCT_NAME', message='Invalid product name. Special characters allowed are _ , @ . / # & + -', regex='^[ \\w\\$\\_\\,\\@\\.\\/\\#\\&\\+\\-\\(\\)]*$')]),
        ),
        migrations.AlterField(
            model_name='flavor',
            name='flavor_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_PRODUCT_NAME', message='Invalid product name. Special characters allowed are _ , @ . / # & + -', regex='^[ \\w\\$\\_\\,\\@\\.\\/\\#\\&\\+\\-\\(\\)]*$')]),
        ),
        migrations.AlterField(
            model_name='fragrance',
            name='fragrance_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_PRODUCT_NAME', message='Invalid product name. Special characters allowed are _ , @ . / # & + -', regex='^[ \\w\\$\\_\\,\\@\\.\\/\\#\\&\\+\\-\\(\\)]*$')]),
        ),
        migrations.AlterField(
            model_name='packagesize',
            name='pack_size_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_PRODUCT_NAME', message='Invalid product name. Special characters allowed are _ , @ . / # & + -', regex='^[ \\w\\$\\_\\,\\@\\.\\/\\#\\&\\+\\-\\(\\)]*$')]),
        ),
        migrations.AlterField(
            model_name='size',
            name='size_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_PRODUCT_NAME', message='Invalid product name. Special characters allowed are _ , @ . / # & + -', regex='^[ \\w\\$\\_\\,\\@\\.\\/\\#\\&\\+\\-\\(\\)]*$')]),
        ),
        migrations.AlterField(
            model_name='weight',
            name='weight_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_PRODUCT_NAME', message='Invalid product name. Special characters allowed are _ , @ . / # & + -', regex='^[ \\w\\$\\_\\,\\@\\.\\/\\#\\&\\+\\-\\(\\)]*$')]),
        ),
    ]