# Generated by Django 2.1 on 2018-11-29 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0015_auto_20181129_1508'),
    ]

    operations = [
        migrations.AlterField(
            model_name='size',
            name='size_name',
            field=models.SlugField(),
        ),
    ]
