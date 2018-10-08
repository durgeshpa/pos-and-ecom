# Generated by Django 2.1 on 2018-10-04 17:48

import adminsortable.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_name', models.CharField(max_length=255)),
                ('category_slug', models.SlugField()),
                ('category_desc', models.TextField(blank=True, null=True)),
                ('category_sku_part', models.CharField(max_length=2, unique=True)),
                ('category_image', models.ImageField(blank=True, null=True, upload_to='category_img')),
                ('is_created', models.DateTimeField(auto_now_add=True)),
                ('is_modified', models.DateTimeField(auto_now=True)),
                ('status', models.BooleanField(default=True)),
                ('category_parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cat_parent', to='categories.Category')),
            ],
        ),
        migrations.CreateModel(
            name='CategoryData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_data_order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
                ('category_data', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='category_posation_data', to='categories.Category')),
            ],
            options={
                'ordering': ['category_data_order'],
            },
        ),
        migrations.CreateModel(
            name='CategoryPosation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('posation_name', models.CharField(max_length=255)),
                ('category_posation_order', models.PositiveIntegerField(db_index=True, default=0, editable=False)),
            ],
            options={
                'ordering': ['category_posation_order'],
            },
        ),
        migrations.AddField(
            model_name='categorydata',
            name='category_pos',
            field=adminsortable.fields.SortableForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cat_data', to='categories.CategoryPosation'),
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('category_slug', 'category_parent')},
        ),
    ]
