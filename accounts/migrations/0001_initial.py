# Generated by Django 2.1 on 2022-04-04 16:24

import accounts.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('first_name', models.CharField(max_length=254)),
                ('last_name', models.CharField(max_length=254)),
                ('phone_number', models.CharField(max_length=10, unique=True, validators=[django.core.validators.RegexValidator(message='Phone number is not valid', regex='^[6-9]\\d{9}$')])),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('user_photo', models.ImageField(blank=True, null=True, upload_to='user_photos/')),
                ('user_type', models.PositiveSmallIntegerField(choices=[(1, 'Administrator'), (2, 'Distributor Executive'), (3, 'Distributor Manager'), (4, 'Operation Executive'), (5, 'Operation Manager'), (6, 'Sales Executive'), (7, 'Sales Manager')], default='6', null=True)),
                ('imei_no', models.CharField(blank=True, max_length=20, null=True)),
                ('is_whatsapp', models.BooleanField(default=False)),
                ('is_ecom_user', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', accounts.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='AppVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_version', models.CharField(max_length=200)),
                ('update_recommended', models.BooleanField(default=False)),
                ('app_type', models.CharField(choices=[('delivery', 'delivery'), ('retailer', 'retailer'), ('ecommerce', 'ecommerce'), ('pos', 'pos'), ('warehouse', 'warehouse')], default='retailer', max_length=50)),
                ('force_update_required', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_document_type', models.CharField(choices=[('pc', 'PAN Card'), ('dl', 'Driving License'), ('uidai', 'Aadhaar Card'), ('pp', 'Passport'), ('vc', 'Voter Card')], default='uidai', max_length=100)),
                ('user_document_number', models.CharField(max_length=100)),
                ('user_document_photo', models.FileField(null=True, upload_to='user_photos/documents/')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_documents', to='accounts.User')),
            ],
            options={
                'verbose_name': 'User Document',
            },
        ),
        migrations.CreateModel(
            name='UserWithName',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('accounts.user',),
            managers=[
                ('objects', accounts.models.UserManager()),
            ],
        ),
    ]
