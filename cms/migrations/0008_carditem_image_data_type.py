# Generated by Django 2.2 on 2022-06-08 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0007_auto_20220602_1231'),
    ]

    operations = [
        migrations.AddField(
            model_name='carditem',
            name='image_data_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Product'), (2, 'Category'), (3, 'Brand'), (4, 'Landing Page'), (5, 'B2C Category')], null=True),
        ),
    ]