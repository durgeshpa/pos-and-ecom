# Generated by Django 2.1 on 2022-04-14 17:06

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('notification_center', '0002_auto_20220404_1624'),
    ]

    operations = [
        migrations.AddField(
            model_name='fcmdevice',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fcmdevice',
            name='updated_at',
            field=models.DateTimeField(auto_now_add=True, default=1),
            preserve_default=False,
        ),
    ]
