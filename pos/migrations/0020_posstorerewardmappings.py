# Generated by Django 2.1 on 2022-04-19 16:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0008_auto_20220419_1635'),
        ('pos', '0019_auto_20220419_1602'),
    ]

    operations = [
        migrations.CreateModel(
            name='PosStoreRewardMappings',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('shops.shop',),
        ),
    ]
