# Generated by Django 2.1 on 2022-05-04 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
        ('retailer_to_sp', '0004_auto_20220503_1557'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='categories.Category'),
        ),
    ]