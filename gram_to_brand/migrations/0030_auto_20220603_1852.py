# Generated by Django 2.2 on 2022-06-03 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0029_auto_20220603_1833'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='po_type',
            field=models.CharField(blank=True, choices=[('grocery', 'Grocery'), ('superstore', 'SuperStore')], default='grocery', max_length=50),
        ),
    ]
