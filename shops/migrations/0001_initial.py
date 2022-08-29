# Generated by Django 2.1 on 2022-04-04 16:24

import datetime
import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import shops.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0001_initial'),
        ('accounts', '0001_initial'),
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='BeatPlanning',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.BooleanField(default=True)),
                ('executive', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_executive', to='accounts.User', verbose_name='Sales Executive')),
                ('manager', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_manager', to='accounts.User')),
            ],
        ),
        migrations.CreateModel(
            name='DayBeatPlanning',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shop_category', models.CharField(choices=[('P1', 'P1'), ('P2', 'P2'), ('P3', 'P3'), ('P4', 'P4')], default='P1', max_length=25)),
                ('beat_plan_date', models.DateField(default=datetime.date.today)),
                ('next_plan_date', models.DateField(default=datetime.date.today)),
                ('temp_status', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('beat_plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='beat_plan', to='shops.BeatPlanning')),
            ],
        ),
        migrations.CreateModel(
            name='ExecutiveFeedback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('executive_feedback', models.CharField(choices=[(1, 'Place Order'), (2, 'No Order For Today'), (3, 'Price Not Matching'), (4, 'Stock Not Available'), (5, 'Could Not Visit'), (6, 'Shop Closed'), (7, 'Owner NA'), (8, 'BDA on Leave'), (9, 'Already ordered today')], max_length=25)),
                ('feedback_date', models.DateField(blank=True, null=True)),
                ('feedback_time', models.TimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('latitude', models.DecimalField(decimal_places=15, max_digits=30, null=True)),
                ('longitude', models.DecimalField(decimal_places=15, max_digits=30, null=True)),
                ('is_valid', models.BooleanField(default=False)),
                ('distance_in_km', models.DecimalField(decimal_places=15, max_digits=30, null=True)),
                ('last_shop_distance', models.DecimalField(decimal_places=15, max_digits=30, null=True)),
                ('day_beat_plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='day_beat_plan', to='shops.DayBeatPlanning')),
            ],
        ),
        migrations.CreateModel(
            name='FavouriteProduct',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='FOFOConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shop_opening_timing', models.TimeField(blank=True, null=True)),
                ('shop_closing_timing', models.TimeField(blank=True, null=True)),
                ('working_off_start_date', models.DateField(blank=True, null=True)),
                ('working_off_end_date', models.DateField(blank=True, null=True)),
                ('delivery_redius', models.DecimalField(blank=True, decimal_places=1, help_text='Insert value in meters', max_digits=8, null=True)),
                ('min_order_value', models.DecimalField(blank=True, decimal_places=2, default=199, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(199)])),
                ('delivery_time', models.IntegerField(blank=True, help_text='Insert value in minutes', null=True)),
            ],
            options={
                'permissions': (('has_fofo_config_operations_shop', 'Has update FOFO  shop config operations'),),
            },
        ),
        migrations.CreateModel(
            name='FOFOConfigCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', shops.fields.CaseInsensitiveCharField(max_length=125, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='FOFOConfigSubCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', shops.fields.CaseInsensitiveCharField(max_length=125)),
                ('type', models.CharField(choices=[('str', 'String'), ('int', 'Integer'), ('float', 'Float'), ('bool', 'Boolean')], default='int', max_length=20)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fofo_category_details', to='shops.FOFOConfigCategory')),
            ],
        ),
        migrations.CreateModel(
            name='FOFOConfigurations',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('key', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fofo_category', to='shops.FOFOConfigSubCategory')),
            ],
            options={
                'permissions': (('has_fofo_config_operations', 'Has update FOFO config operations'),),
            },
        ),
        migrations.CreateModel(
            name='ParentRetailerMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='PosShopUserMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_type', models.CharField(choices=[('manager', 'Manager'), ('store_manager', 'Store Manager'), ('cashier', 'Cashier'), ('delivery_person', 'Delivery Person')], default='cashier', max_length=20)),
                ('is_delivery_person', models.BooleanField(default=False)),
                ('status', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='pos_shop_created_by', to='accounts.User')),
            ],
            options={
                'verbose_name': 'POS Shop User Mapping',
                'verbose_name_plural': 'POS Shop User Mappings',
            },
        ),
        migrations.CreateModel(
            name='RetailerType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('retailer_type_name', models.CharField(choices=[('gm', 'General Merchant'), ('ps', 'Pan Shop'), ('foco', 'Franchise Company Operated'), ('fofo', 'Franchise Franchise Operated')], default='gm', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='SalesAppVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_version', models.CharField(max_length=200)),
                ('update_recommended', models.BooleanField(default=False)),
                ('force_update_required', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Shop',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shop_name', models.CharField(max_length=255)),
                ('enable_loyalty_points', models.BooleanField(blank=True, default=True, null=True)),
                ('shop_code', models.CharField(blank=True, max_length=1, null=True)),
                ('shop_code_bulk', models.CharField(blank=True, max_length=1, null=True)),
                ('shop_code_discounted', models.CharField(blank=True, max_length=1, null=True)),
                ('warehouse_code', models.CharField(blank=True, max_length=3, null=True)),
                ('imei_no', models.CharField(blank=True, max_length=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approval_status', models.IntegerField(choices=[(1, 'Awaiting Approval'), (2, 'Approved'), (0, 'Disapproved')], default=1)),
                ('disapproval_status_reason', models.CharField(blank=True, choices=[('BUSINESS_CLOSED', 'Business Closed'), ('BLOCKED_BY_GRAMFACTORY', 'Blocked By Gramfactory'), ('NOT_SERVING_SHOP_LOCATION', 'Not Serving Shop Location'), ('PERMANENTLY_CLOSED', 'Permanently Closed'), ('REGION_NOT_SERVICED', 'Region Not Serviced'), ('MISBEHAVIOUR_OR_DISPUTE', 'Misbehaviour Or Dispute'), ('MULTIPLE_SHOP_IDS', 'Multiple Shop Ids'), ('FREQUENT_CANCELLATION_HOLD_AND_RETURN_OF_ORDERS', 'Frequent Cancellation, Return And Holds Of Orders'), ('MOBILE_NUMBER_LOST_CLOSED_CHANGED', 'Mobile Number Changed')], max_length=50, null=True)),
                ('status', models.BooleanField(default=False)),
                ('pos_enabled', models.BooleanField(default=False, verbose_name='Enabled For POS')),
                ('latitude', models.DecimalField(decimal_places=15, max_digits=30, null=True, verbose_name='Latitude For Ecommerce')),
                ('longitude', models.DecimalField(decimal_places=15, max_digits=30, null=True, verbose_name='Longitude For Ecommerce')),
                ('online_inventory_enabled', models.BooleanField(default=True, verbose_name='Online Inventory Enabled')),
                ('cutoff_time', models.TimeField(blank=True, null=True)),
                ('dynamic_beat', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_created_by', to='accounts.User')),
                ('favourite_products', models.ManyToManyField(through='shops.FavouriteProduct', to='products.Product')),
                ('related_users', models.ManyToManyField(blank=True, related_name='related_shop_user', to='accounts.User')),
                ('shop_owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_owner_shop', to='accounts.User')),
            ],
            options={
                'permissions': (('can_see_all_shops', 'Can See All Shops'), ('can_do_reconciliation', 'Can Do Reconciliation'), ('can_sales_person_add_shop', 'Can Sales Person Add Shop'), ('can_sales_manager_add_shop', 'Can Sales Manager Add Shop'), ('is_delivery_boy', 'Is Delivery Boy'), ('hide_related_users', 'Hide Related User')),
            },
        ),
        migrations.CreateModel(
            name='ShopAdjustmentFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock_adjustment_file', models.FileField(upload_to='stock_adjustment')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='stock_adjust_by', to='accounts.User')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_adjustment_shop', to='shops.Shop')),
            ],
        ),
        migrations.CreateModel(
            name='ShopDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shop_document_type', models.CharField(choices=[('gstin', 'GSTIN'), ('sln', 'Shop License No'), ('uidai', 'Aadhaar Card'), ('bill', 'Shop Electricity Bill'), ('pan', 'Pan Card No'), ('passport', 'Passport'), ('fssai', 'Fssai License No'), ('dl', 'Driving Licence'), ('ec', 'Election Card'), ('wsvd', 'Weighing Scale Verification Document'), ('drugl', 'Drug License'), ('ua', 'Udyog Aadhar')], default='gstin', max_length=100)),
                ('shop_document_number', models.CharField(max_length=100)),
                ('shop_document_photo', models.FileField(blank=True, null=True, upload_to='shop_photos/shop_name/documents/')),
                ('shop_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_name_documents', to='shops.Shop')),
            ],
        ),
        migrations.CreateModel(
            name='ShopInvoicePattern',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pattern', models.CharField(blank=True, max_length=15, null=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('ACT', 'Active'), ('DIS', 'Disabled')], max_length=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoice_pattern', to='shops.Shop')),
            ],
        ),
        migrations.CreateModel(
            name='ShopMigrationMapp',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gf_addistro_shop', models.IntegerField(default=0)),
                ('sp_gfdn_shop', models.IntegerField(default=0)),
                ('new_sp_addistro_shop', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='ShopPhoto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shop_photo', models.FileField(upload_to='shop_photos/shop_name/')),
                ('shop_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_name_photos', to='shops.Shop')),
            ],
        ),
        migrations.CreateModel(
            name='ShopRequestBrand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('brand_name', models.CharField(blank=True, max_length=100, null=True)),
                ('product_sku', models.CharField(blank=True, max_length=100, null=True)),
                ('request_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_request_brand', to='shops.Shop')),
            ],
        ),
        migrations.CreateModel(
            name='ShopStatusLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(blank=True, max_length=125, null=True)),
                ('status_change_reason', models.CharField(blank=True, max_length=255, null=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_detail', to='shops.Shop')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_status_changed_by', to='accounts.User')),
            ],
        ),
        migrations.CreateModel(
            name='ShopTiming',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('open_timing', models.TimeField()),
                ('closing_timing', models.TimeField()),
                ('break_start_time', models.TimeField(blank=True, null=True)),
                ('break_end_time', models.TimeField(blank=True, null=True)),
                ('off_day', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, choices=[('SUN', 'SUN'), ('MON', 'MON'), ('TUE', 'TUE'), ('WED', 'WED'), ('THU', 'THU'), ('FRI', 'FRI'), ('SAT', 'FRI')], max_length=25, null=True), blank=True, null=True, size=None)),
                ('shop', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_timing', to='shops.Shop')),
            ],
        ),
        migrations.CreateModel(
            name='ShopType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('status', models.BooleanField(default=True)),
                ('shop_type', models.CharField(choices=[('sp', 'Service Partner'), ('r', 'Retailer'), ('sr', 'Super Retailer'), ('gf', 'Gram Factory'), ('f', 'Franchise'), ('dc', 'Dispatch Center')], default='r', max_length=50)),
                ('shop_min_amount', models.FloatField(default=0)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='accounts.User', verbose_name='Created by')),
                ('shop_sub_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shop_sub_type_shop', to='shops.RetailerType')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_type_updated_by', to='accounts.User')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ShopUserMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('status', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='accounts.User', verbose_name='Created by')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_employee', to='accounts.User')),
                ('employee_group', models.ForeignKey(default='1', on_delete=django.db.models.deletion.SET_DEFAULT, related_name='shop_user_group', to='auth.Group')),
                ('manager', models.ForeignKey(blank=True, limit_choices_to={'employee_group__permissions__codename': 'can_sales_manager_add_shop', 'manager': None, 'status': True}, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='employee_list', to='shops.ShopUserMapping')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_user', to='shops.Shop')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_user_mapping_updated_by', to='accounts.User')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='shop',
            name='shop_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_type_shop', to='shops.ShopType'),
        ),
        migrations.AddField(
            model_name='shop',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_uploaded_by', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='posshopusermapping',
            name='shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pos_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='posshopusermapping',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pos_shop_user', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='parentretailermapping',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parrent_mapping', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='parentretailermapping',
            name='retailer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='retiler_mapping', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='fofoconfigurations',
            name='shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fofo_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='fofoconfig',
            name='shop',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fofo_shop_config', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='favouriteproduct',
            name='buyer_shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_favourite', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='favouriteproduct',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_favourite', to='products.Product'),
        ),
        migrations.AddField(
            model_name='daybeatplanning',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shop_id', to='shops.Shop'),
        ),
        migrations.CreateModel(
            name='ShopNameDisplay',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('shops.shop',),
        ),
        migrations.AlterUniqueTogether(
            name='posshopusermapping',
            unique_together={('shop', 'user')},
        ),
        migrations.AlterUniqueTogether(
            name='parentretailermapping',
            unique_together={('parent', 'retailer')},
        ),
        migrations.AlterUniqueTogether(
            name='fofoconfigsubcategory',
            unique_together={('category', 'name')},
        ),
    ]
