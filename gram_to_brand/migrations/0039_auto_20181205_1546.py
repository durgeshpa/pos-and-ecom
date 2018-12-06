# Generated by Django 2.1 on 2018-12-05 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0038_auto_20181201_1720'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartproductmapping',
            name='case_size',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='cartproductmapping',
            name='total_price',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='grnorderproductmapping',
            name='already_grned_product',
            field=models.PositiveIntegerField(blank=True, default=0, verbose_name='Already GRNed Product Quantity'),
        ),
    ]
