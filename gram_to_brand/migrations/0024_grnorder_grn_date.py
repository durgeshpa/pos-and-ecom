# Generated by Django 2.1 on 2018-11-22 13:22

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0023_auto_20181122_1239'),
    ]

    operations = [
        migrations.AddField(
            model_name='grnorder',
            name='grn_date',
            field=models.DateField(auto_now_add=True, default=datetime.datetime(2018, 11, 22, 13, 22, 37, 997489)),
            preserve_default=False,
        ),
    ]