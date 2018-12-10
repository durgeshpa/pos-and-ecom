# Generated by Django 2.1 on 2018-12-06 16:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0009_auto_20181206_1625'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='category_parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cat_parent', to='categories.Category'),
        ),
    ]
