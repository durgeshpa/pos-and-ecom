# Generated by Django 2.2 on 2022-06-10 12:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0031_auto_20220608_1148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='po_type',
            field=models.CharField(blank=True, choices=[('grocery', 'Grocery'), ('superstore', 'SuperStore')], default='grocery', max_length=50),
        ),
    ]
