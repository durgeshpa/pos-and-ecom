# Generated by Django 2.2 on 2022-06-02 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0011_remove_grnorder_total_freight_charges'),
    ]

    operations = [
        migrations.AddField(
            model_name='grnorder',
            name='total_freight_charges',
            field=models.DecimalField(decimal_places=4, default='0.0000', max_digits=20),
        ),
    ]
