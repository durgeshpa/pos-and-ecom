# Generated by Django 2.1 on 2018-12-17 12:53

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0030_auto_20181210_1257'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvendormapping',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productvendormapping',
            name='modified_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
