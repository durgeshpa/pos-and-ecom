# Generated by Django 2.1 on 2018-11-23 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0027_auto_20181122_1940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartproductmapping',
            name='price',
            field=models.FloatField(default=0, verbose_name='Gram To Brand Price'),
        ),
    ]