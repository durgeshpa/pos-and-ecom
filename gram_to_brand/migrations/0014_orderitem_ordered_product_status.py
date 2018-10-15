# Generated by Django 2.1 on 2018-10-15 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gram_to_brand', '0013_auto_20181015_1728'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='ordered_product_status',
            field=models.CharField(blank=True, choices=[('partially_delivered', 'Partially Delivered'), ('delivered', 'Delivered')], max_length=50, null=True),
        ),
    ]
