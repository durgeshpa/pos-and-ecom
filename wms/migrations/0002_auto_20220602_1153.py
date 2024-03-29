# Generated by Django 2.2 on 2022-06-02 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wms', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bininternalinventorychange',
            name='to_be_picked_qty',
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='bininternalinventorychange',
            name='transaction_type',
            field=models.CharField(blank=True, choices=[('warehouse_adjustment', 'WareHouse Adjustment'), ('reserved', 'Reserved'), ('ordered', 'Ordered'), ('released', 'Released'), ('canceled', 'Canceled'), ('audit_adjustment', 'Audit Adjustment'), ('put_away_type', 'Put Away'), ('pickup_created', 'Pickup Created'), ('pickup_complete', 'Pickup Complete'), ('picking_cancelled', 'Pickup Cancelled'), ('picked', 'Picked'), ('stock_correction_in_type', 'stock_correction_in_type'), ('stock_correction_out_type', 'stock_correction_out_type'), ('expired', 'expired'), ('manual_audit_add', 'Manual Audit Add'), ('manual_audit_deduct', 'Manual Audit Deduct'), ('audit_correction_add', 'Audit Correction Add'), ('audit_correction_deduct', 'Audit Correction Deduct'), ('franchise_batch_in', 'Franchise Batch In'), ('franchise_sales', 'Franchise Sales'), ('franchise_returns', 'Franchise Returns'), ('repackaging', 'Repackaging'), ('moved_to_discounted', 'Moved To Discounted'), ('added_as_discounted', 'Added As Discounted'), ('bin_shift', 'Bin Shift'), ('bin_shift_add', 'Bin Shift Add'), ('bin_shift_deduct', 'Bin Shift Deduct')], max_length=25, null=True),
        ),
    ]
