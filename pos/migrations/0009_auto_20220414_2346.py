# Generated by Django 2.1 on 2022-04-14 23:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0008_auto_20220414_2307'),
    ]

    operations = [
        migrations.AlterField(
            model_name='posstorerewardmapping',
            name='value_of_each_point',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]