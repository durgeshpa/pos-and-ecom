# Generated by Django 2.1 on 2022-04-04 16:24

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
                ('name', models.CharField(blank=True, max_length=20, null=True)),
                ('image', models.FileField(blank=True, null=True, upload_to='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('banner_start_date', models.DateTimeField(blank=True, null=True)),
                ('banner_end_date', models.DateTimeField(blank=True, null=True)),
                ('banner_type', models.CharField(blank=True, choices=[('brand', 'brand'), ('subbrand', 'subbrand'), ('category', 'category'), ('subcategory', 'subcategory'), ('product', 'product'), ('offer', 'offer')], max_length=255, null=True)),
                ('status', models.BooleanField(default=True, help_text='Designates whether the banner is to be displayed or not.', verbose_name='Status')),
                ('alt_text', models.CharField(blank=True, max_length=20, null=True)),
                ('text_below_image', models.CharField(blank=True, max_length=20, null=True)),
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
                ('banner_position_order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
            ],
            options={
                'verbose_name': 'Banner Position',
                'verbose_name_plural': 'Banner Positions',
                'ordering': ['banner_position_order'],
            },
        ),
        migrations.CreateModel(
            name='BannerSlot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'verbose_name': 'Banner Slot',
                'verbose_name_plural': 'Banner Slots',
            },
        ),
        migrations.CreateModel(
            name='HomePageMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=255, unique=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'HomePage Message',
                'verbose_name_plural': 'HomePage Messages',
            },
        ),
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='bannerslot',
            name='page',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='banner.Page'),
        ),
        migrations.AddField(
            model_name='bannerposition',
            name='bannerslot',
            field=models.ForeignKey(max_length=255, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='banner.BannerSlot'),
        ),
    ]