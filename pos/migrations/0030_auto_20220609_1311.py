# Generated by Django 2.2 on 2022-06-09 13:11

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('retailer_to_sp', '0015_orderedproduct_shipment_label_pdf'),
        ('pos', '0029_auto_20220609_1310'),
    ]

    operations = [
        migrations.AddField(
            model_name='postrip',
            name='shipment',
            field=models.ForeignKey(default=django.utils.timezone.now, on_delete=django.db.models.deletion.CASCADE, related_name='pos_trips', to='retailer_to_sp.OrderedProduct'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='postrip',
            name='trip_end_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='postrip',
            name='trip_start_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='postrip',
            name='trip_type',
            field=models.CharField(choices=[('ECOM', 'Ecom'), ('SUPERSTORE', 'SUPERSTORE')], default=django.utils.timezone.now, max_length=10),
            preserve_default=False,
        ),
    ]
