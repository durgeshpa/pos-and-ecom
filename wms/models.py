import sys

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.db.models import Sum, Q
from django.db.models import query, manager
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.safestring import mark_safe
from model_utils import Choices

from common.common_utils import barcode_gen
from products.models import Product, ParentProduct
from shops.models import Shop

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
    ('total_available', 'TOTAL AVAILABLE'),  # Total physical inventory available(available+reserved+ordered)
    ('available', 'AVAILABLE'),  # Inventory Available
    ('reserved', 'RESERVED'),  # Inventory Reserved
    ('shipped', 'SHIPPED'),  # Inventory Shipped
    ('to_be_picked', 'TO BE PICKED'),  # Inventory Available
    ('ordered', 'Ordered'),  # Inventory Ordered
    ('picked', 'PICKED'),  # Inventory picked
    ('canceled', 'Canceled'),  # Inventory Canceled
    ('new', 'New'),
    ('repackaging', 'Repackaging')
)


class BaseTimestampModel(models.Model):
    """
        Abstract Model to have helper fields of created_at and updated_at
    """
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)

    class Meta:
        abstract = True


class BaseTimestampUserModel(models.Model):
    """
        Abstract Model to have helper fields of created_at, created_by, updated_at and updated_by
    """
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)
    created_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Created by",
        related_name="%(app_label)s_%(class)s_created_by",
        on_delete=models.DO_NOTHING
    )
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Updated by",
        related_name="%(app_label)s_%(class)s_updated_by",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        abstract = True


class Zone(BaseTimestampUserModel):
    """
        Mapping model of warehouse, supervisor, coordinator and putaway users
    """
    zone_number = models.CharField(max_length=20, null=True, blank=True, editable=False)
    name = models.CharField(max_length=30, null=True)
    warehouse = models.ForeignKey(Shop, null=True, on_delete=models.DO_NOTHING)
    supervisor = models.ForeignKey(get_user_model(), related_name='supervisor_zone_user', on_delete=models.CASCADE)
    coordinator = models.ForeignKey(get_user_model(), related_name='coordinator_zone_user', on_delete=models.CASCADE)
    putaway_users = models.ManyToManyField(get_user_model(), related_name='putaway_zone_users')
    picker_users = models.ManyToManyField(get_user_model(), related_name='picker_zone_users')

    class Meta:
        permissions = (
            ("can_have_zone_warehouse_permission", "Can have Zone Warehouse Permission"),
            ("can_have_zone_supervisor_permission", "Can have Zone Supervisor Permission"),
            ("can_have_zone_coordinator_permission", "Can have Zone Coordinator Permission"),
        )

    def __str__(self):
        return str(self.zone_number) + " - " + str(self.name)


class ZonePutawayUserAssignmentMapping(BaseTimestampModel):
    """
        Mapping model of zone and putaway user where we maintain the last assigned user for next assignment
    """
    zone = models.ForeignKey(Zone, related_name="zone_putaway_assigned_users", on_delete=models.DO_NOTHING)
    user = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    last_assigned_at = models.DateTimeField(verbose_name="Last Assigned At", null=True)

    def __str__(self):
        return str(self.zone) + " - " + str(self.user)


class ZonePickerUserAssignmentMapping(BaseTimestampModel):
    """
        Mapping model of zone and picker user where we maintain the last assigned user for next assignment
    """
    zone = models.ForeignKey(Zone, related_name="zone_picker_assigned_users", on_delete=models.DO_NOTHING)
    user = models.ForeignKey(get_user_model(), related_name='picker_assigned_zone', on_delete=models.DO_NOTHING)
    last_assigned_at = models.DateTimeField(verbose_name="Last Assigned At", null=True)
    user_enabled = models.BooleanField(default=True)
    alternate_user = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.DO_NOTHING)

    def __str__(self):
        return str(self.zone) + " - " + str(self.user)


class WarehouseAssortment(BaseTimestampUserModel):
    """
        Mapping model of warehouse, product and zone
    """
    warehouse = models.ForeignKey(Shop, null=True, on_delete=models.DO_NOTHING)
    product = models.ForeignKey(ParentProduct, related_name='product_zones', on_delete=models.DO_NOTHING)
    zone = models.ForeignKey(Zone, on_delete=models.DO_NOTHING)

    def __str__(self):
        return str(self.product) + " - " + str(self.zone) + " - " + str(self.pk)


class BaseQuerySet(query.QuerySet):

    def update(self, **kwargs):
        kwargs['modified_at'] = timezone.now()
        super().update(**kwargs)


class Manager(manager.BaseManager.from_queryset(BaseQuerySet)):
    pass


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
    bin_barcode_txt = models.CharField(max_length=20, null=True, blank=True)
    bin_barcode = models.ImageField(upload_to='images/', blank=True, null=True)
    zone = models.ForeignKey(Zone, null=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.bin_id

    def save(self, *args, **kwargs):
        image = barcode_gen(str(self.bin_barcode_txt))
        self.bin_barcode = InMemoryUploadedFile(image, 'ImageField', "%s.jpg" % self.bin_id, 'image/jpeg',sys.getsizeof(image), None)
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
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Weight In gm')
    to_be_picked_qty = models.PositiveIntegerField(verbose_name='To Be Picked', default=0)
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

    def save(self, *args, **kwargs):
        if self.weight is None:
            self.weight = 0
        super(BinInventory, self).save(*args, **kwargs)

    class Meta:
        db_table = "wms_bin_inventory"


class WarehouseInventory(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', related_name='related_sku', on_delete=models.DO_NOTHING)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Weight In gm')
    in_stock = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    visible = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.weight is None:
            self.weight = 0
        super(WarehouseInventory, self).save(*args, **kwargs)

    class Meta:
        db_table = "wms_warehouse_inventory"


class In(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    in_type = models.CharField(max_length=20, null=True, blank=True)
    in_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING, related_name='ins')
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING, related_name='+')
    quantity = models.PositiveIntegerField()
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Weight In gm')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    manufacturing_date = models.DateField(null=True)
    expiry_date = models.DateField(null=True)

    def save(self, *args, **kwargs):
        if self.weight is None:
            self.weight = 0
        super(In, self).save(*args, **kwargs)

class Putaway(models.Model):
    NEW, ASSIGNED, INITIATED, COMPLETED, CANCELLED = 'NEW', 'ASSIGNED', 'INITIATED', 'COMPLETED', 'CANCELLED'
    PUTAWAY_STATUS_CHOICE = Choices((NEW, 'New'), (ASSIGNED, 'Assigned'), (INITIATED, 'Initiated'),
                                    (COMPLETED, 'Completed'), (CANCELLED, 'Cancelled'))
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    putaway_user = models.ForeignKey(get_user_model(), null=True, blank=True, related_name='putaway_user',
                                     on_delete=models.DO_NOTHING)
    putaway_type = models.CharField(max_length=20, null=True, blank=True)
    putaway_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    putaway_quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    status = models.CharField(max_length=10, choices=PUTAWAY_STATUS_CHOICE, null=True, blank=True)
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
    REMARK_CHOICE = Choices((0, 'NOT_ENOUGH_SPACE', 'Not enough space'))
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, blank=True, null=True, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    putaway_type = models.CharField(max_length=50, null=True, blank=True)
    putaway = models.ForeignKey(Putaway, null=True, blank=True, on_delete=models.DO_NOTHING, verbose_name="putaway")
    bin = models.ForeignKey(BinInventory, null=True, blank=True, on_delete=models.DO_NOTHING)
    putaway_quantity = models.PositiveIntegerField()
    putaway_status = models.BooleanField(default=False)
    remark = models.CharField(choices=REMARK_CHOICE, max_length=20, null=True, blank=True)
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
    out_type = models.CharField(max_length=50, null=True, blank=True)
    out_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING, related_name='outs')
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Weight In gm')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.weight is None:
            self.weight = 0
        super(Out, self).save(*args, **kwargs)


class Pickup(models.Model):

    objects = Manager()
    pickup_status_choices = Choices(
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
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    pickup_quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    out = models.ForeignKey(Out, null=True, blank=True, on_delete=models.DO_NOTHING)
    zone = models.ForeignKey(Zone, null=True, blank=True, related_name='pickup_zone', on_delete=models.DO_NOTHING)
    status = models.CharField(max_length=21, null=True, blank=True, choices=pickup_status_choices)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True)


class PickupBinInventory(models.Model):
    PICKUP_REMARKS_CHOICES = Choices((0, '--', '--'),
                                     (1, 'EXPIRED', 'Near Expiry / Expired'),
                                     (2, 'DAMAGED', 'Damaged'),
                                     (3, 'NOT_FOUND', 'Item not found'),
                                     (4, 'MRP_DIFF', 'Different MRP'),
                                     (5, 'GRAMMAGE_DIFF', 'Different Grammage'),
                                     (6, 'NOT_CLEAN', 'Item not clean'))

    PICKUP_STATUS_CHOICES = Choices((0, 'PENDING', 'Pickup Pending'),
                                    (1, 'PARTIAL', 'Partially Completed'),
                                    (2, 'FULL', 'Fully Completed'),
                                    (3, 'CANCELLED', 'Pickup Cancelled'))
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    pickup = models.ForeignKey(Pickup, related_name='bin_inventory', null=True, blank=True, on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    bin = models.ForeignKey(BinInventory, null=True, blank=True, on_delete=models.DO_NOTHING)
    bin_zone = models.ForeignKey(Zone, null=True, blank=True, related_name='pickup_bin_zone', on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    pickup_quantity = models.PositiveIntegerField(null=True, default=None)
    bin_quantity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    shipment_batch = models.ForeignKey('retailer_to_sp.OrderedProductBatch', null=True, related_name='rt_pickup_batch_mapping',
                                       default=None,on_delete=models.DO_NOTHING)
    last_picked_at = models.DateTimeField(null=True)
    remarks = models.CharField(choices=PICKUP_REMARKS_CHOICES, max_length=100, null=True)
    audit_no = models.CharField(max_length=100, null=True)

    class Meta:
        db_table = "wms_pickup_bin_inventory"


class StockMovementCSVUpload(models.Model):
    upload_inventory_type = (
        (1, "-"),
        (2, "Bin Stock Movement"),
        (3, "Stock Correction"),
        (4, "WareHouse Inventory Change"),
        (5, "Packing Material Stock Correction")
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
        ('order_cancelled', 'Order Cancelled'),
        ('audit_adjustment', 'Audit Adjustment'),
        ('put_away_type', 'Put Away'),
        ('pickup_created', 'Pickup Created'),
        ('picked', 'Picked'),
        ('picking_cancelled', 'Picking Cancelled'),
        ('pickup_complete', 'Pickup Complete'),
        ('shipped_out', 'Shipped Out'),
        ('stock_correction_in_type', 'stock_correction_in_type'),
        ('stock_correction_out_type', 'stock_correction_out_type'),
        ('reschedule', 'Reschedule'),
        ('expired', 'Expired'),
        ('repackaging', 'Repackaging'),
        ('manual_audit_add', 'Manual Audit Add'),
        ('manual_audit_deduct', 'Manual Audit Deduct'),
        ('audit_correction_add', 'Audit Correction Add'),
        ('audit_correction_deduct', 'Audit Correction Deduct'),
        ('franchise_batch_in', 'Franchise Batch In'),
        ('franchise_sales', 'Franchise Sales'),
        ('franchise_returns', 'Franchise Returns'),
        ('moved_to_discounted', 'Moved To Discounted'),
        ('added_as_discounted', 'Added As Discounted')
    )

    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, null=True, blank=True, on_delete=models.DO_NOTHING)
    transaction_type = models.CharField(max_length=25, null=True, blank=True, choices=transaction_type)
    transaction_id = models.CharField(max_length=25, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, blank=True, on_delete=models.DO_NOTHING)
    initial_type = models.ForeignKey(InventoryType, related_name='initial_type', null=True, blank=True,
                                     on_delete=models.DO_NOTHING)
    final_type = models.ForeignKey(InventoryType, related_name='final_type', null=True, blank=True,
                                   on_delete=models.DO_NOTHING)
    initial_stage = models.ForeignKey(InventoryState, related_name='initial_stage', null=True, blank=True,
                                      on_delete=models.DO_NOTHING)
    final_stage = models.ForeignKey(InventoryState, related_name='final_stage', null=True, blank=True,
                                    on_delete=models.DO_NOTHING)
    quantity = models.IntegerField(null=True, blank=True, default=0)
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Weight In gm')
    inventory_csv = models.ForeignKey(StockMovementCSVUpload, null=True, blank=True, on_delete=models.DO_NOTHING)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.transaction_type

    def save(self, *args, **kwargs):
        if self.weight is None:
            self.weight = 0
        super(WarehouseInternalInventoryChange, self).save(*args, **kwargs)

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
        ('put_away_type', 'Put Away'),
        ('pickup_created', 'Pickup Created'),
        ('pickup_complete', 'Pickup Complete'),
        ('picking_cancelled', 'Pickup Cancelled'),
        ('stock_correction_in_type', 'stock_correction_in_type'),
        ('stock_correction_out_type', 'stock_correction_out_type'),
        ('expired', 'expired'),
        ('manual_audit_add', 'Manual Audit Add'),
        ('manual_audit_deduct', 'Manual Audit Deduct'),
        ('audit_correction_add', 'Audit Correction Add'),
        ('audit_correction_deduct', 'Audit Correction Deduct'),
        ('franchise_batch_in', 'Franchise Batch In'),
        ('franchise_sales', 'Franchise Sales'),
        ('franchise_returns', 'Franchise Returns'),
        ('repackaging', 'Repackaging'),
        ('moved_to_discounted', 'Moved To Discounted'),
        ('added_as_discounted', 'Added As Discounted'),
        ('bin_shift', 'Bin Shift'),

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
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Weight In gm')
    inventory_csv = models.ForeignKey(StockMovementCSVUpload, null=True, blank=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.weight is None:
            self.weight = 0
        super(BinInternalInventoryChange, self).save(*args, **kwargs)

    class Meta:
        db_table = "wms_bin_internal_inventory_change"


class StockCorrectionChange(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    stock_sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    stock_bin_id = models.ForeignKey(Bin, related_name='bin', null=True, blank=True, on_delete=models.DO_NOTHING)
    correction_type = models.CharField(max_length=10, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Weight In gm')
    inventory_csv = models.ForeignKey(StockMovementCSVUpload, null=True, blank=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.weight is None:
            self.weight = 0
        super(StockCorrectionChange, self).save(*args, **kwargs)

    class Meta:
        db_table = "wms_stock_correction_change"


class OrderReserveRelease(models.Model):
    release_type = (
        ('cron', "CRON"),
        ('manual', "Manual"),
    )
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    transaction_id = models.CharField(max_length=25, null=True, blank=True)
    warehouse_internal_inventory_reserve = models.ForeignKey(WarehouseInternalInventoryChange,
                                                             related_name='internal_inventory_reserve',
                                                             null=True, blank=True, on_delete=models.DO_NOTHING)
    warehouse_internal_inventory_release = models.ForeignKey(WarehouseInternalInventoryChange,
                                                             related_name='internal_inventory_release',
                                                             null=True, blank=True, on_delete=models.DO_NOTHING)
    release_type = models.CharField(max_length=25, choices=release_type, null=True, blank=True)
    ordered_quantity = models.PositiveIntegerField(null=True, blank=True)
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

@receiver(post_save, sender=Bin)
def create_order_id(sender, instance=None, created=False, **kwargs):
    if created:
        instance.bin_barcode_txt = '1' + str(instance.id).zfill(11)
        instance.save()


class ExpiredInventoryMovement(models.Model):
    STATUS_CHOICE = Choices((0,'OPEN','open'),(1,'CLOSED','closed'))
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.DO_NOTHING)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    expiry_date = models.DateField()
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICE, default=STATUS_CHOICE.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class PosInventoryState(models.Model):
    NEW, AVAILABLE, ORDERED, SHIPPED = 'new', 'available', 'ordered', 'shipped'
    POS_INVENTORY_STATES = (
        (NEW, 'New'),
        (AVAILABLE, 'Available'),
        (ORDERED, 'Ordered'),
        (SHIPPED, 'Shipped')
    )
    inventory_state = models.CharField(max_length=20, choices=POS_INVENTORY_STATES, unique=True)

    def __str__(self):
        return self.inventory_state


class PosInventory(models.Model):
    product = models.ForeignKey("pos.RetailerProduct", on_delete=models.DO_NOTHING, related_name='pos_inventory_product')
    quantity = models.IntegerField(default=0)
    inventory_state = models.ForeignKey(PosInventoryState, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'inventory_state',)


class PosInventoryChange(models.Model):
    ORDERED, CANCELLED, RETURN, STOCK_ADD, STOCK_UPDATE, GRN_ADD, GRN_UPDATE = 'ordered', 'order_cancelled',\
                                                                               'order_return', 'stock_add',\
                                                                               'stock_update', 'grn_add', 'grn_update'
    SHIPPED = 'shipped'
    transaction_type = (
        (ORDERED, "Ordered"),
        (CANCELLED, 'Order Cancelled'),
        (RETURN, 'Order Return'),
        (STOCK_ADD, 'Stock Add'),
        (STOCK_UPDATE, 'Stock Update'),
        (GRN_ADD, 'GRN Add'),
        (GRN_UPDATE, 'GRN Update'),
        (SHIPPED, 'Shipped')
    )
    product = models.ForeignKey("pos.RetailerProduct", on_delete=models.DO_NOTHING)
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=25, choices=transaction_type)
    transaction_id = models.CharField(max_length=25)
    initial_state = models.ForeignKey(PosInventoryState, related_name='pos_inv_initial_state', on_delete=models.DO_NOTHING)
    final_state = models.ForeignKey(PosInventoryState, related_name='pos_inv_final_state', on_delete=models.DO_NOTHING)
    changed_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class QCArea(BaseTimestampUserModel):
    QC_AREA_TYPE_CHOICES = Choices(('OA', 'Open Area'), ('RC', 'Rack'), ('PA', 'Pallet'))
    warehouse = models.ForeignKey(Shop, null=True, on_delete=models.DO_NOTHING)
    area_id = models.CharField(max_length=6, null=True, blank=True)
    area_type = models.CharField(max_length=50, choices=QC_AREA_TYPE_CHOICES)
    area_barcode_txt = models.CharField(max_length=20, null=True, blank=True)
    area_barcode = models.ImageField(upload_to='images/', blank=True, null=True)
    is_active = models.BooleanField()

    def __str__(self):
        if self.warehouse:
            return self.area_id + " - " + str(self.warehouse.pk)
        return self.area_id

    def save(self, *args, **kwargs):

        if not self.id:
            last_qc_area = QCArea.objects.filter(area_type=self.area_type, warehouse=self.warehouse).last()
            if not last_qc_area:
                current_number = 0
            else:
                current_number = int(last_qc_area.area_id[2:])
            current_number += 1
            self.area_id = self.area_type + str(current_number).zfill(4)
        super(QCArea, self).save(*args, **kwargs)

    @property
    def barcode_image(self):
        return mark_safe('<img alt="%s" src="%s" />' % (self.area_id, self.area_barcode.url))
