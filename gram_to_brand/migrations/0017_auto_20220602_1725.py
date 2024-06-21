# Generated by Django 2.2 on 2022-06-02 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0016_grnorder_discount_charges'),
    ]

    operations = [
        migrations.AddField(
            model_name='grnorder',
            name='insurance_charges',
            field=models.DecimalField(decimal_places=4, default='0.0000', max_digits=20),
        ),
        migrations.AddField(
            model_name='grnorder',
            name='other_charges',
            field=models.DecimalField(decimal_places=4, default='0.0000', max_digits=20),
        ),
        migrations.AddField(
            model_name='grnorder',
            name='total_grn_amount',
            field=models.DecimalField(decimal_places=4, default='0.0000', max_digits=20),
        ),
    ]