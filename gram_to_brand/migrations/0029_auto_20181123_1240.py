# Generated by Django 2.1 on 2018-11-23 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0028_auto_20181123_1058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartproductmapping',
            name='price',
            field=models.FloatField(default=0, verbose_name='Brand To Gram Price'),
        ),
    ]
