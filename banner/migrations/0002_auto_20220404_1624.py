# Generated by Django 2.1 on 2022-04-04 16:24

import adminsortable.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('shops', '0001_initial'),
        ('banner', '0001_initial'),
        ('addresses', '0002_auto_20220404_1624'),
        ('products', '0001_initial'),
        ('categories', '0001_initial'),
        ('brand', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bannerposition',
            name='buyer_shop',
            field=models.ManyToManyField(blank=True, related_name='buyer_shop_banner', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='bannerposition',
            name='city',
            field=models.ManyToManyField(blank=True, related_name='city_banner', to='addresses.City'),
        ),
        migrations.AddField(
            model_name='bannerposition',
            name='page',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='banner.Page'),
        ),
        migrations.AddField(
            model_name='bannerposition',
            name='pincode',
            field=models.ManyToManyField(blank=True, related_name='pincode_banner', to='addresses.Pincode'),
        ),
        migrations.AddField(
            model_name='bannerposition',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='shops.Shop', verbose_name='Seller Shop'),
        ),
        migrations.AddField(
            model_name='bannerdata',
            name='banner_data',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='banner_position_data', to='banner.Banner'),
        ),
        migrations.AddField(
            model_name='bannerdata',
            name='slot',
            field=adminsortable.fields.SortableForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ban_data', to='banner.BannerPosition'),
        ),
        migrations.AddField(
            model_name='banner',
            name='brand',
            field=models.ForeignKey(blank=True, max_length=255, null=True, on_delete=django.db.models.deletion.CASCADE, to='brand.Brand'),
        ),
        migrations.AddField(
            model_name='banner',
            name='category',
            field=models.ForeignKey(blank=True, max_length=255, null=True, on_delete=django.db.models.deletion.CASCADE, to='categories.Category'),
        ),
        migrations.AddField(
            model_name='banner',
            name='products',
            field=models.ManyToManyField(blank=True, to='products.Product'),
        ),
        migrations.AddField(
            model_name='banner',
            name='sub_brand',
            field=models.ForeignKey(blank=True, max_length=255, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='banner_subbrand', to='brand.Brand'),
        ),
        migrations.AddField(
            model_name='banner',
            name='sub_category',
            field=models.ForeignKey(blank=True, max_length=255, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='banner_subcategory', to='categories.Category'),
        ),
    ]
