# Generated by Django 2.1 on 2022-04-04 16:24

from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('payments', '0001_initial'),
        ('retailer_to_sp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShipmentData',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.orderedproduct',),
        ),
        migrations.CreateModel(
            name='ShipmentPaymentApproval',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.orderedproduct',),
        ),
        migrations.CreateModel(
            name='ShipmentPaymentEdit',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.orderedproduct',),
        ),
    ]