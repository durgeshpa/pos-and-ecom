# Generated by Django 2.1 on 2018-10-16 15:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0017_orderitem_changed_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderitem',
            name='changed_price',
        ),
    ]
