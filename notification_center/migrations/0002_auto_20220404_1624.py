# Generated by Django 2.1 on 2022-04-04 16:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('notification_center', '0001_initial'),
        ('shops', '0001_initial'),
        ('accounts', '0001_initial'),
        ('addresses', '0002_auto_20220404_1624'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupnotificationscheduler',
            name='buyer_shops',
            field=models.ManyToManyField(blank=True, related_name='notification_shops', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='groupnotificationscheduler',
            name='city',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notification_city', to='addresses.City'),
        ),
        migrations.AddField(
            model_name='groupnotificationscheduler',
            name='pincode',
            field=models.ManyToManyField(blank=True, related_name='notification_pincodes', to='addresses.Pincode'),
        ),
        migrations.AddField(
            model_name='groupnotificationscheduler',
            name='seller_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notification_seller_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='groupnotificationscheduler',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_scheduler', to='notification_center.Template'),
        ),
        migrations.AddField(
            model_name='gcmactivity',
            name='notification',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notification_center.Notification'),
        ),
        migrations.AddField(
            model_name='fcmdevice',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_fcm', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='emailactivity',
            name='notification',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='notification_center.Notification'),
        ),
        migrations.AlterUniqueTogether(
            name='template',
            unique_together={('name', 'type')},
        ),
        migrations.AlterUniqueTogether(
            name='notification',
            unique_together={('user', 'template')},
        ),
    ]