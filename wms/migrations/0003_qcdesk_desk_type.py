# Generated by Django 2.2 on 2022-06-02 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wms', '0002_auto_20220602_1153'),
    ]

    operations = [
        migrations.AddField(
            model_name='qcdesk',
            name='desk_type',
            field=models.CharField(choices=[('GROCERY', 'Grocery'), ('SUPERSTORE', 'Super Store')], default='GROCERY', max_length=15, null=True),
        ),
    ]