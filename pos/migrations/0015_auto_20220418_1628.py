# Generated by Django 2.1 on 2022-04-18 16:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0014_shoprewardconfig_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shoprewardconfigration',
            name='shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_reward_mapping', to='pos.ShopRewardConfig'),
        ),
    ]
