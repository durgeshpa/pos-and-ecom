# Generated by Django 2.1 on 2018-10-05 17:53

import adminsortable.fields
import brand.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('brand_name', models.CharField(max_length=20)),
                ('brand_logo', models.FileField(upload_to='', validators=[brand.models.validate_image])),
                ('brand_description', models.CharField(max_length=30)),
                ('brand_code', models.CharField(max_length=2)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('active_status', models.PositiveSmallIntegerField(choices=[(1, 'Active'), (2, 'Inactive')], default='1', verbose_name='Active Status')),
            ],
        ),
        migrations.CreateModel(
            name='BrandData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('brand_data_order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
                ('brand_data', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='brand_position_data', to='brand.Brand')),
            ],
            options={
                'ordering': ['brand_data_order'],
            },
        ),
        migrations.CreateModel(
            name='BrandPosition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position_name', models.CharField(max_length=255)),
                ('brand_position_order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
            ],
            options={
                'ordering': ['brand_position_order'],
            },
        ),
        migrations.AddField(
            model_name='branddata',
            name='slot',
            field=adminsortable.fields.SortableForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='brand_data', to='brand.BrandPosition'),
        ),
    ]
