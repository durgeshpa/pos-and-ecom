# Generated by Django 2.2 on 2022-06-13 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0017_shop_superstore_enable'),
    ]

    operations = [
        migrations.AddField(
            model_name='shop',
            name='shop_code_super_store',
            field=models.CharField(blank=True, max_length=1, null=True),
        ),
    ]
