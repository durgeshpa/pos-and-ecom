# Generated by Django 2.1 on 2022-04-06 21:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_remove_parentproduct_tax_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='parentproduct',
            name='tax_status',
            field=models.CharField(blank=True, choices=[('PENDING', 'Pending For Approval'), ('APPROVED', 'Approved'), ('DECLINED', 'Declined')], max_length=10, null=True),
        ),
    ]