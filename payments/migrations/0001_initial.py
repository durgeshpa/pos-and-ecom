# Generated by Django 2.1 on 2022-04-04 16:24

import django.core.validators
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OrderPayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.CharField(blank=True, max_length=50, null=True)),
                ('paid_amount', models.DecimalField(decimal_places=4, default='0.0000', max_digits=20, validators=[django.core.validators.MinValueValidator(0)])),
                ('payment_id', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OrderPaymentStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.CharField(blank=True, max_length=50, null=True)),
                ('payment_status', models.CharField(blank=True, choices=[('PENDING', 'Pending'), ('PARTIALLY_PAID', 'Partially_paid'), ('PAID', 'Paid')], max_length=50, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.CharField(blank=True, max_length=100, null=True)),
                ('reference_no', models.CharField(blank=True, max_length=50, null=True)),
                ('paid_amount', models.DecimalField(decimal_places=4, default='0.0000', max_digits=20, validators=[django.core.validators.MinValueValidator(0)])),
                ('payment_mode_name', models.CharField(choices=[('cash_payment', 'Cash Payment'), ('online_payment', 'Online Payment'), ('credit_payment', 'Credit Payment'), ('wallet_payment', 'Wallet Payment')], default='cash_payment', max_length=50)),
                ('prepaid_or_postpaid', models.CharField(blank=True, choices=[('prepaid', 'prepaid'), ('postpaid', 'postpaid')], max_length=50, null=True)),
                ('payment_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('payment_approval_status', models.CharField(blank=True, choices=[('pending_approval', 'pending_approval'), ('approved_and_verified', 'approved_and_verified'), ('rejected', 'rejected')], default='pending_approval', max_length=50, null=True)),
                ('payment_received', models.DecimalField(decimal_places=4, default='0.0000', max_digits=20, validators=[django.core.validators.MinValueValidator(0)])),
                ('is_payment_approved', models.BooleanField(default=False)),
                ('mark_as_settled', models.BooleanField(default=False)),
                ('payment_status', models.CharField(blank=True, choices=[('not_initiated', 'not_initiated'), ('initiated', 'initiated'), ('cancelled', 'cancelled'), ('failure', 'failure'), ('completed', 'completed')], default='initiated', max_length=50, null=True)),
                ('online_payment_type', models.CharField(blank=True, choices=[('UPI', 'UPI'), ('NEFT', 'NEFT'), ('IMPS', 'IMPS'), ('RTGS', 'RTGS')], max_length=50, null=True)),
                ('initiated_time', models.DateTimeField(blank=True, null=True)),
                ('timeout_time', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PaymentImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_document_type', models.CharField(choices=[('payment_screenshot', 'payment_screenshot')], default='payment_screenshot', max_length=100)),
                ('reference_image', models.FileField(upload_to='payment/screenshot/')),
            ],
            options={
                'verbose_name': 'Payment Screenshot',
            },
        ),
        migrations.CreateModel(
            name='PaymentMode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_mode_name', models.CharField(blank=True, choices=[('cash_payment', 'Cash Payment'), ('online_payment', 'Online Payment'), ('credit_payment', 'Credit Payment'), ('wallet_payment', 'Wallet Payment')], max_length=50, null=True)),
                ('status', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='ShipmentPayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.CharField(blank=True, max_length=50, null=True)),
                ('paid_amount', models.DecimalField(decimal_places=4, default='0.0000', max_digits=20, validators=[django.core.validators.MinValueValidator(0)])),
            ],
        ),
        migrations.CreateModel(
            name='ShipmentPaymentStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.CharField(blank=True, max_length=50, null=True)),
                ('payment_status', models.CharField(blank=True, choices=[('PENDING', 'Pending'), ('PARTIALLY_PAID', 'Partially_paid'), ('PAID', 'Paid')], max_length=50, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]