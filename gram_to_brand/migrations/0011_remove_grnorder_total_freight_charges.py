# Generated by Django 2.2 on 2022-06-02 17:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0010_grnorder_tcs_amount'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='grnorder',
            name='total_freight_charges',
        ),
    ]
