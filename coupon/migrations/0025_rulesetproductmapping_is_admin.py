# Generated by Django 2.2 on 2022-06-23 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon', '0024_auto_20220622_1642'),
    ]

    operations = [
        migrations.AddField(
            model_name='rulesetproductmapping',
            name='is_admin',
            field=models.BooleanField(blank=True, default=False),
        ),
    ]
