# Generated by Django 2.1 on 2018-11-29 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0019_auto_20181129_1533'),
    ]

    operations = [
        migrations.AlterField(
            model_name='packagesize',
            name='pack_size_name',
            field=models.SlugField(unique=True),
        ),
    ]