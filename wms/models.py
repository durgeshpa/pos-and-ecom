from django.db import models
from products.models import Product
from shops.models import Shop
from common.common_utils import barcode_gen
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.safestring import mark_safe
import sys
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from django.contrib import messages
from datetime import datetime, timedelta
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model

BIN_TYPE_CHOICES = (
    ('PA', 'Pallet'),
    ('SR', 'Slotted Rack'),
    ('HD', 'Heavy Duty Rack')
)

INVENTORY_TYPE_CHOICES = (
    ('normal', 'NORMAL'),  # Inventory Available For Order
    ('expired', 'EXPIRED'),  # Inventory Expired
    ('damaged', 'DAMAGED'),  # Inventory Damaged
    ('discarded', 'DISCARDED'),  # Inventory Rejected
    ('disposed', 'DISPOSED'),  # Inventory Disposed
    ('missing', 'MISSING'),  # Inventory Missing
    ('returned', 'RETURNED'),
    ('new', 'New')
)

INVENTORY_STATE_CHOICES = (
    ('available', 'AVAILABLE'),  # Inventory Available
    ('reserved', 'RESERVED'),  # Inventory Reserved
    ('shipped', 'SHIPPED'),  # Inventory Shipped
    ('ordered', 'Ordered'),  # Inventory Ordered
    ('picked', 'PICKED'),  # Inventory picked
    ('canceled', 'Canceled'),  # Inventory Canceled
    ('new', 'New')
)


class InventoryType(models.Model):
    inventory_type = models.CharField(max_length=20, choices=INVENTORY_TYPE_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.inventory_type

    class Meta:
        db_table = "wms_inventory_type"


class InventoryState(models.Model):
    inventory_state = models.CharField(max_length=20, choices=INVENTORY_STATE_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.inventory_state

    class Meta:
        db_table = "wms_inventory_state"


class Bin(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    bin_id = models.CharField(max_length=20, null=True, blank=True)
    bin_type = models.CharField(max_length=50, choices=BIN_TYPE_CHOICES, default='PA')
    is_active = models.BooleanField()
    bin_barcode = models.ImageField(upload_to='images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.bin_id

    def save(self, *args, **kwargs):
        image = barcode_gen(str(self.bin_id))
        self.bin_barcode = InMemoryUploadedFile(image, 'ImageField', "%s.jpg" % self.bin_id, 'image/jpeg',
                                                sys.getsizeof(image), None)
        super(Bin, self).save(*args, **kwargs)

    @property
    def barcode_image(self):
        return mark_safe('<img alt="%s" src="%s" />' % (self.bin_id, self.bin_barcode.url))


class BinInventory(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', related_name='rt_product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    in_stock = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def available_qty(cls, shop_id, sku_id):
        return cls.objects.filter(Q(warehouse__id=shop_id),
                                  Q(sku__id=sku_id),
                                  Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')

    @classmethod
    def available_qty_with_inventory_type(cls, shop_id, sku_id, inventory_type):
        return cls.objects.filter(Q(warehouse__id=shop_id),
                                  Q(sku__id=sku_id), Q(inventory_type__id=inventory_type),
                                  Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = "wms_bin_inventory"


class WarehouseInventory(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', related_name='related_sku', on_delete=models.DO_NOTHING)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    in_stock = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_warehouse_inventory"


class In(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    in_type = models.CharField(max_length=20, null=True, blank=True)
    in_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Putaway(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    putaway_user = models.ForeignKey(get_user_model(), null=True, blank=True, related_name='putaway_user',
                                     on_delete=models.DO_NOTHING)
    putaway_type = models.CharField(max_length=20, null=True, blank=True)
    putaway_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    putaway_quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)

    def clean(self):
        super(Putaway, self).clean()
        self.putaway_quantity = 0 if not self.putaway_quantity else self.putaway_quantity
        if self.putaway_quantity > self.quantity:
            raise ValidationError('Putaway_quantity must be less than or equal to Grned_quantity')


class PutawayBinInventory(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, blank=True, null=True, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    putaway_type = models.CharField(max_length=50, null=True, blank=True)
    putaway = models.ForeignKey(Putaway, null=True, blank=True, on_delete=models.DO_NOTHING, verbose_name="putaway")
    bin = models.ForeignKey(BinInventory, null=True, blank=True, on_delete=models.DO_NOTHING)
    putaway_quantity = models.PositiveIntegerField()
    putaway_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    # def save(self, *args, **kwargs):
    #     check_quantity = PutawayBinInventory.objects.filter(putaway=self.putaway.id).aggregate(total=Sum('putaway_quantity')).get('total')
    #     if not check_quantity:
    #         check_quantity=0
    #     if check_quantity <= Putaway.objects.filter(id=self.putaway.id).last().quantity:
    #         super(PutawayBinInventory, self).save(*args, **kwargs)

    class Meta:
        db_table = "wms_putaway_bin_inventory"

    def __str__(self):
        return self.putaway.batch_id


class Out(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    out_type = models.CharField(max_length=20, null=True, blank=True)
    out_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Pickup(models.Model):
    pickup_status_choices = (
        ('pickup_creation', 'PickUp Creation'),
        ('picking_assigned', 'Pickup Assigned'),
        ('picking_complete', 'Pickup Complete'),
        ('picking_cancelled', 'Pickup Cancelled'),
    )
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    pickup_type = models.CharField(max_length=20, null=True, blank=True)
    pickup_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', related_name='rt_product_pickup',
                            on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    pickup_quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    out = models.ForeignKey(Out, null=True, blank=True, on_delete=models.DO_NOTHING)
    status = models.CharField(max_length=21, null=True, blank=True, choices=pickup_status_choices)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class PickupBinInventory(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    pickup = models.ForeignKey(Pickup, null=True, blank=True, on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    bin = models.ForeignKey(BinInventory, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    pickup_quantity = models.PositiveIntegerField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_pickup_bin_inventory"


class StockMovementCSVUpload(models.Model):
    upload_inventory_type = (
        (1, "-"),
        (2, "Bin Stock Movement"),
        (3, "Stock Correction"),
        (4, "WareHouse Inventory Change"),

    )

    uploaded_by = models.ForeignKey(get_user_model(), related_name='inventory_manager', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    upload_csv = models.FileField(upload_to='shop_photos/shop_name/documents/inventory/', null=True, blank=True)
    inventory_movement_type = models.CharField(max_length=25, choices=upload_inventory_type, default=1)

    class Meta:
        db_table = "wms_stock_movement_csv_upload"

    def __str__(self):
        return str(self.id)


class WarehouseInternalInventoryChange(models.Model):
    transaction_type = (
        ('warehouse_adjustment', "WareHouse Adjustment"),
        ('reserved', "Reserved"),
        ('ordered', "Ordered"),
        ('released', "Released"),
        ('canceled', 'Canceled'),
        ('audit_adjustment', 'Audit Adjustment'),
        ('put_away_type', 'Put Away Type'),

    )

    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, null=True, blank=True, on_delete=models.DO_NOTHING)
    transaction_type = models.CharField(max_length=25, null=True, blank=True, choices=transaction_type)
    transaction_id = models.CharField(max_length=25, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    initial_type = models.ForeignKey(InventoryType, related_name='initial_type', null=True, blank=True,
                                     on_delete=models.DO_NOTHING)
    final_type = models.ForeignKey(InventoryType, related_name='final_type', null=True, blank=True,
                                   on_delete=models.DO_NOTHING)
    initial_stage = models.ForeignKey(InventoryState, related_name='initial_stage', null=True, blank=True,
                                      on_delete=models.DO_NOTHING)
    final_stage = models.ForeignKey(InventoryState, related_name='final_stage', null=True, blank=True,
                                    on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    inventory_csv = models.ForeignKey(StockMovementCSVUpload, null=True, blank=True, on_delete=models.DO_NOTHING)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.transaction_type

    class Meta:
        db_table = "wms_warehouse_internal_inventory_change"


class BinInternalInventoryChange(models.Model):
    bin_transaction_type = (
        ('warehouse_adjustment', "WareHouse Adjustment"),
        ('reserved', "Reserved"),
        ('ordered', "Ordered"),
        ('released', "Released"),
        ('canceled', 'Canceled'),
        ('audit_adjustment', 'Audit Adjustment'),
        ('put_away_type', 'Put Away Type'),

    )
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    initial_inventory_type = models.ForeignKey(InventoryType, related_name='initial_inventory_type', null=True,
                                               blank=True, on_delete=models.DO_NOTHING)
    final_inventory_type = models.ForeignKey(InventoryType, related_name='final_inventory_type', null=True, blank=True,
                                             on_delete=models.DO_NOTHING)
    initial_bin = models.ForeignKey(Bin, related_name='initial_bin', null=True, blank=True, on_delete=models.DO_NOTHING)
    final_bin = models.ForeignKey(Bin, related_name='final_bin', null=True, blank=True, on_delete=models.DO_NOTHING)
    transaction_type = models.CharField(max_length=25, null=True, blank=True, choices=bin_transaction_type)
    transaction_id = models.CharField(max_length=25, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    inventory_csv = models.ForeignKey(StockMovementCSVUpload, null=True, blank=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_bin_internal_inventory_change"


class StockCorrectionChange(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    stock_sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    stock_bin_id = models.ForeignKey(Bin, related_name='bin', null=True, blank=True, on_delete=models.DO_NOTHING)
    correction_type = models.CharField(max_length=10, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    inventory_csv = models.ForeignKey(StockMovementCSVUpload, null=True, blank=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_stock_correction_change"


class OrderReserveRelease(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    warehouse_internal_inventory_reserve = models.ForeignKey(WarehouseInternalInventoryChange,
                                                             related_name='internal_inventory_reserve',
                                                             null=True, blank=True, on_delete=models.DO_NOTHING)
    warehouse_internal_inventory_release = models.ForeignKey(WarehouseInternalInventoryChange,
                                                             related_name='internal_inventory_release',
                                                             null=True, blank=True, on_delete=models.DO_NOTHING)
    reserved_time = models.DateTimeField(null=True, blank=True)
    release_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Audit(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    uploaded_by = models.ForeignKey(get_user_model(), related_name='audit_user', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    upload_csv = models.FileField(upload_to='shop_photos/shop_name/documents/audit/', null=True, blank=True)

    class Meta:
        db_table = "wms_audit"

    def __str__(self):
        return str(self.id)
