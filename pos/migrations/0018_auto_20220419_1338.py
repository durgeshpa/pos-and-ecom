# Generated by Django 2.1 on 2022-04-19 13:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0017_auto_20220418_2357'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shoprewardconfigration',
            name='key',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_reward_key', to='shops.FOFOConfigSubCategory'),
        ),
    ]
