# Generated by Django 2.2 on 2022-06-17 15:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0008_carditem_image_data_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='carddata',
            name='template',
        ),
        migrations.RemoveField(
            model_name='carditem',
            name='image_data_type',
        ),
        migrations.DeleteModel(
            name='Template',
        ),
    ]
