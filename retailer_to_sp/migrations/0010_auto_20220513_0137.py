# Generated by Django 2.1 on 2022-05-13 01:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('retailer_to_sp', '0009_auto_20220513_0027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='redeem_factor',
            field=models.FloatField(default=0),
        ),
    ]