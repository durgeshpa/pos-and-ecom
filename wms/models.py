from django.db import models
from products.models import Product
from shops.models import Shop
from common.common_utils import barcode_gen
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.safestring import mark_safe
import sys
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model



BIN_TYPE_CHOICES = (
    ('p', 'Pallet'),
    ('sr', 'Slotted Rack'),
)

INVENTORY_TYPE_CHOICES = (
    ('normal', 'NORMAL'),  #Available For Order
    ('expired', 'EXPIRED'), #Expiry date passed
    ('damaged', 'DAMAGED'), #Not orderable
    ('discarded', 'DISCARDED'), #Rejected by warehouse
    ('disposed', 'DISPOSED'), #Rejected or Expired and removed from warehouse
)

INVENTORY_STATE_CHOICES = (
    ('available', 'AVAILABLE'),
    ('reserved', 'RESERVED'),
    ('shipped', 'SHIPPED'),
)
class InventoryType(models.Model):
    # id = models.AutoField(primary_key=True)
    inventory_type = models.CharField(max_length=20,choices=INVENTORY_TYPE_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.inventory_type

    class Meta:
        db_table = "wms_inventory_type"


class InventoryState(models.Model):
    # id = models.AutoField(primary_key=True)
    inventory_state = models.CharField(max_length=20, choices=INVENTORY_STATE_CHOICES,null=True, blank=True)

    def __str__(self):
        return self.inventory_state

    class Meta:
        db_table = "wms_inventory_state"


class Bin(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    bin_id = models.CharField(max_length=20, null=True, blank=True)
    bin_type = models.CharField(max_length=50, choices=BIN_TYPE_CHOICES, default='p')
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

    # @property
    # def decoded_barcode(self):
    #     return barcode_decoder(self.bin_barcode)


class BinInventory(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop,null=True, blank=True, on_delete=models.DO_NOTHING)
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku',related_name='rt_product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=21, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    # inventory_state = models.ForeignKey(InventoryState, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    in_stock = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def available_qty(cls, shop_id, sku_id):
        return cls.objects.filter(Q(warehouse__id=shop_id),
                                  Q(sku__id=sku_id),
                                  Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')



    class Meta:
        db_table = "wms_bin_inventory"


class BinInternalInventoryChange(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=21, null=True, blank=True)
    initial_inventory_type = models.ForeignKey(InventoryType,related_name='initial_inventory_type', null=True, blank=True, on_delete=models.DO_NOTHING)
    final_inventory_type = models.ForeignKey(InventoryType,related_name='final_inventory_type', null=True, blank=True, on_delete=models.DO_NOTHING)
    initial_bin = models.ForeignKey(Bin,related_name='initial_bin', null=True, blank=True, on_delete=models.DO_NOTHING)
    final_bin = models.ForeignKey(Bin,related_name='final_bin', null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wms_bin_internal_inventory_change"


class WarehouseInventory(models.Model):
    # id = models.AutoField(primary_key=True)
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
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    in_type = models.CharField(max_length=20, null=True, blank=True)
    in_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=21, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Putaway(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    putaway_type = models.CharField(max_length=20, null=True, blank=True)
    putaway_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product,to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=21, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    putaway_quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sku.product_sku

    def clean(self):
        super(Putaway, self).clean()
        self.putaway_quantity = 0 if not self.putaway_quantity else self.putaway_quantity
        if self.putaway_quantity > self.quantity:
            raise ValidationError('Putaway_quantity must be less than or equal to Grned_quantity')


class PutawayBinInventory(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    putaway = models.ForeignKey(Putaway, null=True, blank=True, on_delete=models.DO_NOTHING)
    bin = models.ForeignKey(BinInventory, null=True, blank=True, on_delete=models.DO_NOTHING)
    putaway_quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        check_quantity = PutawayBinInventory.objects.filter(putaway=self.putaway.id).aggregate(total=Sum('putaway_quantity')).get('total')
        if not check_quantity:
            check_quantity=0
        if check_quantity < Putaway.objects.filter(id=self.putaway.id).last().quantity:
            super(PutawayBinInventory, self).save(*args, **kwargs)

    class Meta:
        db_table = "wms_putaway_bin_inventory"

    def __str__(self):
        return self.putaway.batch_id


class Out(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    out_type = models.CharField(max_length=20, null=True, blank=True)
    out_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Pickup(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    pickup_type = models.CharField(max_length=20, null=True, blank=True)
    pickup_type_id = models.CharField(max_length=20, null=True, blank=True)
    sku = models.ForeignKey(Product, to_field='product_sku', related_name='rt_product_pickup', on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    pickup_quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    out = models.ForeignKey(Out, null=True, blank=True, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    # def save(self, *args, **kwargs):
    #     if self.pickup_quantity <= self.quantity:
    #         super(Pickup, self).save(*args, *kwargs)


class PickupBinInventory(models.Model):
    # id = models.AutoField(primary_key=True)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    pickup = models.ForeignKey(Pickup, null=True, blank=True, on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=21, null=True, blank=True)
    bin = models.ForeignKey(BinInventory, null=True, blank=True, on_delete=models.DO_NOTHING)
    pickup_quantity = models.PositiveIntegerField()
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
    status = models.BooleanField(default=True)
    upload_csv = models.FileField(upload_to='shop_photos/shop_name/documents/inventory/', null=True, blank=True)
    inventory_movement_type = models.CharField(max_length=25, choices=upload_inventory_type, default=1)

    class Meta:
        db_table = "wms_stock_movement_csv_upload"


class WarehouseInternalInventoryChange(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, null=True, blank=True, on_delete=models.DO_NOTHING)
    transaction_type = models.CharField(max_length=25, null=True, blank=True)
    transaction_id = models.CharField(max_length=25, null=True, blank=True)
    initial_stage = models.CharField(max_length=25, null=True, blank=True)
    final_stage = models.CharField(max_length=25, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.transaction_id

    class Meta:
        db_table = "wms_warehouse_internal_inventory_change"


@receiver(post_save, sender=BinInventory)
def create_warehouse_inventory(sender, instance=None, created=False, *args, **kwargs):

    if created:
        WarehouseInventory.objects.update_or_create(warehouse=instance.warehouse,sku=instance.sku,
                                                    inventory_state=InventoryState.objects.filter(inventory_state='available').last(),
                                                    defaults={
                                                             'inventory_type':InventoryType.objects.filter(inventory_type='normal').last(),
                                                             'inventory_state':InventoryState.objects.filter(inventory_state='available').last(),
                                                             'quantity':BinInventory.available_qty(instance.warehouse.id, instance.sku.id),
                                                             'in_stock':instance.in_stock})
