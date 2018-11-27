# Generated by Django 2.1 on 2018-11-27 12:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('retailer_to_sp', '0011_auto_20181101_1624'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerCare',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('email_us', models.URLField(default='info@grmafactory.com')),
                ('contact_us', models.CharField(default='7607846774', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('order_status', models.CharField(choices=[('pending', 'Pending'), ('resolved', 'Resolved')], default='pending', max_length=20, null=True)),
                ('select_issue', models.CharField(choices=[('cancellation', ' Cancellation'), ('return', 'Return'), ('others', 'Others')], max_length=100, null=True, verbose_name='Issue')),
                ('complaint_detail', models.CharField(max_length=2000, null=True)),
                ('order_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='retailer_to_sp.Order')),
            ],
        ),
    ]
