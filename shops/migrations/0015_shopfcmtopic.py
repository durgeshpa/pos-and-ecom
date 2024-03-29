# Generated by Django 2.1 on 2022-05-03 15:57

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0014_remove_shop_status_reward_configuration'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShopFcmTopic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic_name', models.CharField(max_length=200)),
                ('registration_ids', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), size=None)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fcm_topics', to='shops.Shop', unique=True)),
            ],
            options={
                'verbose_name': 'Shop Fcm Topic',
                'verbose_name_plural': 'Shop Fcm Topics',
            },
        ),
    ]
