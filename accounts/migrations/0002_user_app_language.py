# Generated by Django 2.2 on 2022-08-01 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='app_language',
            field=models.CharField(blank=True, choices=[('hi', 'Hindi'), ('en', 'English')], default='en', max_length=20),
        ),
    ]
