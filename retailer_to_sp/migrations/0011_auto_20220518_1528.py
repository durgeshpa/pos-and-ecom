# Generated by Django 2.1 on 2022-05-18 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('retailer_to_sp', '0010_auto_20220513_0137'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=15, max_digits=30, null=True, verbose_name='Latitude For Ecommerce order'),
        ),
        migrations.AddField(
            model_name='order',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=15, max_digits=30, null=True, verbose_name='Longitude For Ecommerce order'),
        ),
    ]
