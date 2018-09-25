# Generated by Django 2.1 on 2018-09-24 18:21

import adminsortable.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.FileField(upload_to='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.BooleanField(default=True, help_text='Designates whether the banner is to be displayed or not.', verbose_name='Status')),
                ('Type', models.CharField(choices=[('Y', 'Yes'), ('N', 'No')], default='Y', help_text='Designates the type of the banner.', max_length=2, verbose_name='Type')),
            ],
        ),
        migrations.CreateModel(
            name='BannerData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('banner_data_order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
            ],
            options={
                'ordering': ['banner_data_order'],
            },
        ),
        migrations.CreateModel(
            name='BannerPosition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position_name', models.CharField(max_length=255)),
                ('banner_position_order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
            ],
            options={
                'ordering': ['banner_position_order'],
            },
        ),
        migrations.AddField(
            model_name='bannerdata',
            name='banner',
            field=adminsortable.fields.SortableForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ban_data', to='banner.BannerPosition'),
        ),
        migrations.AddField(
            model_name='bannerdata',
            name='banner_data',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='banner_posation_data', to='banner.Banner'),
        ),
    ]
