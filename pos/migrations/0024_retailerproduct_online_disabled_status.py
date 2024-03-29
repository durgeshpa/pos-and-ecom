# Generated by Django 2.1 on 2022-05-04 21:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0023_auto_20220419_2136'),
    ]

    operations = [
        migrations.AddField(
            model_name='retailerproduct',
            name='online_disabled_status',
            field=models.CharField(blank=True, choices=[('out_of_stock', 'Out of Stock'), ('pricing_mismatch', 'Pricing Mismatch'), ('expired', 'Expired'), ('damaged', 'Damaged'), ('wrong_pickup', 'Wrong Pickup')], max_length=50, null=True),
        ),
    ]
