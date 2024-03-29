# Generated by Django 2.1 on 2022-05-03 15:57

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0015_shopfcmtopic'),
        ('accounts', '0001_initial'),
        ('retailer_to_sp', '0003_einvoicedata_enotedata'),
    ]

    operations = [
        migrations.CreateModel(
            name='BuyerPurchaseData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fin_year', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(2019), django.core.validators.MaxValueValidator(2022)])),
                ('total_purchase', models.FloatField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('buyer_shop', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='buyer_purchase', to='shops.Shop')),
                ('seller_shop', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_sale', to='shops.Shop')),
            ],
            options={
                'verbose_name': 'Buyer Purchase',
                'verbose_name_plural': 'Buyer Purchase',
            },
        ),
        migrations.CreateModel(
            name='SearchKeywordLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('search_term', models.CharField(max_length=100, null=True)),
                ('search_frequency', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentmapping',
            name='loaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dc_shipments_loaded', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='invoice_sub_total',
            field=models.FloatField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='invoice_total',
            field=models.FloatField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='is_tcs_applicable',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tcs_amount',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tcs_percent',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentmapping',
            name='loaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='last_shipments_loaded', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='note',
            name='note_total',
            field=models.FloatField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='note',
            name='tcs_amount',
            field=models.FloatField(default=0),
        ),
    ]
