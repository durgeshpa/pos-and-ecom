# Generated by Django 2.1 on 2018-11-22 19:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0026_auto_20181122_1842'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cart',
            old_name='brand_supplier',
            new_name='supplier_name',
        ),
    ]