# Generated by Django 2.1 on 2022-04-04 16:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_sent', models.BooleanField(default=True, verbose_name='E-mail sent')),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
        migrations.CreateModel(
            name='FCMDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dev_id', models.CharField(max_length=50, unique=True, verbose_name='Device ID')),
                ('reg_id', models.CharField(max_length=255, unique=True, verbose_name='Registration ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Name')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is active?')),
            ],
            options={
                'verbose_name': 'Device',
                'verbose_name_plural': 'Devices',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GCMActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gcm_sent', models.BooleanField(default=True)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
        migrations.CreateModel(
            name='GroupNotificationScheduler',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('repeat', models.BigIntegerField(choices=[(3600, 'hourly'), (86400, 'daily'), (604800, 'weekly'), (1209600, 'every 2 weeks'), (2419200, 'every 4 weeks'), (0, 'never')], default=0)),
                ('repeat_until', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='NotificationScheduler',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_at', models.DateTimeField(db_index=True)),
                ('repeat', models.BigIntegerField(choices=[(3600, 'hourly'), (86400, 'daily'), (604800, 'weekly'), (1209600, 'every 2 weeks'), (2419200, 'every 4 weeks'), (0, 'never')], default=0)),
                ('repeat_until', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Template',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('type', models.CharField(choices=[('PO_APPROVED', 'PO approved'), ('PO_CREATED', 'PO created'), ('PO_EDITED', 'PO edited'), ('LOGIN', 'User logged in'), ('SIGNUP', 'User signed up'), ('PASSWORD_RESET', 'User requested password change'), ('SHOP_CREATED', 'User shop created'), ('SHOP_VERIFIED', 'User shop verified'), ('ORDER_CREATED', 'Order created'), ('ORDER_RECEIVED', 'Order received'), ('ORDER_DISPATCHED', 'Order dispatched'), ('ORDER_SHIPPED', 'Order shipped'), ('ORDER_DELIVERED', 'Order delivered'), ('OFFER', 'Offer'), ('SALE', 'Sale'), ('SCHEME', 'Scheme'), ('CUSTOM', 'Custom'), ('PROMOTIONAL', 'Promotional')], default='LOGIN', max_length=255, verbose_name='Type of Template')),
                ('text_email_template', models.TextField(blank=True, null=True, verbose_name='Plain E-mail content')),
                ('html_email_template', models.TextField(blank=True, null=True, verbose_name='HTML E-mail content')),
                ('text_sms_template', models.TextField(blank=True, null=True, verbose_name='Text SMS content')),
                ('voice_call_template', models.TextField(blank=True, null=True, verbose_name='Voice Call content')),
                ('gcm_title', models.CharField(blank=True, max_length=255, null=True, verbose_name='Title for push notification')),
                ('gcm_description', models.TextField(blank=True, max_length=255, null=True, verbose_name='Description for push notification')),
                ('gcm_image', models.ImageField(blank=True, null=True, upload_to='gcm_banner', verbose_name='Banner for push notification')),
                ('gcm_deep_link_url', models.URLField(blank=True, null=True, verbose_name='Deep Linking for push notification')),
                ('email_alert', models.BooleanField(default=True, verbose_name='Enable/Disable email notification')),
                ('text_sms_alert', models.BooleanField(default=True, verbose_name='Enable/Disable sms notification')),
                ('voice_call_alert', models.BooleanField(default=True, verbose_name='Enable/Disable voice call notification')),
                ('gcm_alert', models.BooleanField(default=True, verbose_name='Enable/Disable mobile push notification')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.BooleanField(default=True)),
                ('notification_groups', models.ManyToManyField(blank=True, to='auth.Group')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='TemplateVariable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_variable', models.CharField(blank=True, max_length=255, null=True, verbose_name='Variable in E-mail template')),
                ('text_sms_variable', models.CharField(blank=True, max_length=255, null=True, verbose_name='Variable in SMS template')),
                ('voice_call_variable', models.CharField(blank=True, max_length=255, null=True, verbose_name='Variable in Voice Call template')),
                ('gcm_variable', models.CharField(blank=True, max_length=255, null=True, verbose_name='Variable in Push Notification template')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('template', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='notification_center.Template')),
            ],
            options={
                'ordering': ['template'],
            },
        ),
        migrations.CreateModel(
            name='TextSMSActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_sms_sent', models.BooleanField(default=True, verbose_name='Text SMS sent')),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('notification', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='textsmsactivities', to='notification_center.Notification')),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_notification', models.BooleanField(default=True)),
                ('sms_notification', models.BooleanField(default=True)),
                ('app_notification', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.User')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VoiceCallActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voice_call_sent', models.BooleanField(default=True, verbose_name='Voice Call sent')),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('notification', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='notification_center.Notification')),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
        migrations.AddField(
            model_name='notificationscheduler',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_scheduler', to='notification_center.Template'),
        ),
        migrations.AddField(
            model_name='notificationscheduler',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.User'),
        ),
        migrations.AddField(
            model_name='notification',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='notification_center.Template'),
        ),
        migrations.AddField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.User'),
        ),
    ]