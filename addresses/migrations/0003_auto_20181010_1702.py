# Generated by Django 2.1 on 2018-10-10 17:02

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('addresses', '0002_auto_20181008_1319'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='address_line1',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_NAME', message='Invalid address. Special characters allowed are # - , / . ( ) &', regex='^[\\w*\\s*\\#\\-\\,\\/\\.\\(\\)\\&]*$')]),
        ),
        migrations.AlterField(
            model_name='address',
            name='nick_name',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[django.core.validators.RegexValidator(code='INVALID_NAME', message='Invalid name. Only alphabets are allowed', regex='^[a-zA-Z\\s]{2,255}$')]),
        ),
        migrations.AlterField(
            model_name='area',
            name='area_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_NAME', message='Invalid name. Only alphabets are allowed', regex='^[a-zA-Z\\s]{2,255}$')]),
        ),
        migrations.AlterField(
            model_name='city',
            name='city_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_NAME', message='Invalid name. Only alphabets are allowed', regex='^[a-zA-Z\\s]{2,255}$')]),
        ),
        migrations.AlterField(
            model_name='country',
            name='country_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_NAME', message='Invalid name. Only alphabets are allowed', regex='^[a-zA-Z\\s]{2,255}$')]),
        ),
        migrations.AlterField(
            model_name='state',
            name='state_name',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_NAME', message='Invalid name. Only alphabets are allowed', regex='^[a-zA-Z\\s]{2,255}$')]),
        ),
    ]