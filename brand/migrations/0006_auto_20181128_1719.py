# Generated by Django 2.1 on 2018-11-28 17:19

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('addresses', '0007_address_shop_name'),
        ('brand', '0005_auto_20181123_1136'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=255)),
                ('vendor_name', models.CharField(max_length=255)),
                ('contact_person_name', models.CharField(blank=True, max_length=255, null=True)),
                ('telephone_no', models.CharField(blank=True, max_length=15, null=True)),
                ('mobile', models.CharField(max_length=10)),
                ('designation', models.CharField(max_length=255)),
                ('address_line1', models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(code='INVALID_NAME', message='Invalid address. Special characters allowed are # - , / . ( ) &', regex='^[\\w*\\s*\\#\\-\\,\\/\\.\\(\\)\\&]*$')])),
                ('pincode', models.CharField(blank=True, max_length=6, validators=[django.core.validators.RegexValidator(code='INVALID_PINCODE', message='Invalid Pincode', regex='^[1-9][0-9]{5}$')])),
                ('payment_terms', models.TextField(blank=True, null=True)),
                ('vendor_registion_free', models.CharField(blank=True, choices=[('paid', 'Paid'), ('unpaid', 'Un-Paid')], max_length=50, null=True)),
                ('sku_listing_free', models.CharField(blank=True, choices=[('paid', 'Paid'), ('unpaid', 'Un-Paid')], max_length=50, null=True)),
                ('return_policy', models.TextField(blank=True, null=True)),
                ('GST_number', models.CharField(max_length=100)),
                ('MSMED_reg_no', models.CharField(blank=True, max_length=100, null=True)),
                ('MSMED_reg_document', models.FileField(blank=True, null=True, upload_to='vendor/msmed_doc')),
                ('fssai_licence', models.FileField(blank=True, null=True, upload_to='vendor/fssai_licence_doc')),
                ('GST_document', models.FileField(upload_to='vendor/gst_doc')),
                ('pan_card', models.FileField(upload_to='vendor/pan_card')),
                ('cancelled_cheque', models.FileField(upload_to='vendor/cancelled_cheque')),
                ('list_of_sku_in_NPI_formate', models.FileField(upload_to='vendor/slu_list_in_npi')),
                ('vendor_form', models.FileField(blank=True, null=True, upload_to='vendor/vendor_form')),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vendor_city_address', to='addresses.City')),
                ('state', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vendor_state_address', to='addresses.State')),
            ],
        ),
        migrations.AddField(
            model_name='brand',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vendor_brand', to='brand.Vendor'),
        ),
    ]
