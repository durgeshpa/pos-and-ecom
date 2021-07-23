from django.db import models
from datetime import datetime

from model_utils import Choices
from wms.models import RetailerProduct, PosInventoryState
from products.models import Product
from shops.models import Shop
from wms.models import InventoryType, InventoryState, Bin
# Create your models here.

class OrderDetailReports(models.Model):
    invoice_id = models.CharField(max_length=255, null=True)
    order_invoice = models.CharField(max_length=255, null=True)
    invoice_date = models.CharField(max_length=255, null=True)
    invoice_modified_at = models.CharField(max_length=255, null=True)
    invoice_last_modified_by = models.CharField(max_length=255, null=True)
    invoice_status = models.CharField(max_length=255, null=True)
    order_id = models.CharField(max_length=255, null=True)
    seller_shop = models.CharField(max_length=255, null=True)
    order_status = models.CharField(max_length=255, null=True)
    order_date = models.CharField(max_length=255, null=True)
    order_modified_at = models.CharField(max_length=255, null=True)
    order_by = models.CharField(max_length=255, null=True)
    retailer_id = models.CharField(max_length=255, null=True)
    retailer_name = models.CharField(max_length=255, null=True)
    pin_code = models.CharField(max_length=255, null=True)
    product_id = models.CharField(max_length=255, null=True)
    product_name = models.CharField(max_length=255, null=True)
    product_brand = models.CharField(max_length=255, null=True)
    product_mrp = models.CharField(max_length=255, null=True)
    product_value_tax_included = models.CharField(max_length=255, null=True)
    ordered_sku_pieces = models.CharField(max_length=255, null=True)
    shipped_sku_pieces = models.CharField(max_length=255, null=True)
    delivered_sku_pieces = models.CharField(max_length=255, null=True)
    returned_sku_pieces = models.CharField(max_length=255, null=True)
    damaged_sku_pieces = models.CharField(max_length=255, null=True)
    product_cgst = models.CharField(max_length=255, null=True)
    product_sgst = models.CharField(max_length=255, null=True)
    product_igst = models.CharField(max_length=255, null=True)
    product_cess = models.CharField(max_length=255, null=True)
    sales_person_name = models.CharField(max_length=255, null=True)
    order_type = models.CharField(max_length=255, null=True)
    campaign_name= models.CharField(max_length=255, null=True)
    discount = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return  "%s"%(self.order_invoice)

class OrderReports(models.Model):
    invoice_id = models.CharField(max_length=255, null=True)
    order_invoice = models.CharField(max_length=255, null=True)
    invoice_date = models.CharField(max_length=255, null=True)
    invoice_modified_at = models.CharField(max_length=255, null=True)
    invoice_last_modified_by = models.CharField(max_length=255, null=True)
    invoice_status = models.CharField(max_length=255, null=True)
    order_id = models.CharField(max_length=255, null=True)
    seller_shop = models.CharField(max_length=255, null=True)
    order_status = models.CharField(max_length=255, null=True)
    order_date = models.CharField(max_length=255, null=True)
    order_modified_at = models.CharField(max_length=255, null=True)
    order_by = models.CharField(max_length=255, null=True)
    retailer_id = models.CharField(max_length=255, null=True)
    retailer_name = models.CharField(max_length=255, null=True)
    pin_code = models.CharField(max_length=255, null=True)
    product_id = models.CharField(max_length=255, null=True)
    product_name = models.CharField(max_length=255, null=True)
    product_brand = models.CharField(max_length=255, null=True)
    product_mrp = models.CharField(max_length=255, null=True)
    product_value_tax_included = models.CharField(max_length=255, null=True)
    ordered_sku_pieces = models.CharField(max_length=255, null=True)
    shipped_sku_pieces = models.CharField(max_length=255, null=True)
    delivered_sku_pieces = models.CharField(max_length=255, null=True)
    returned_sku_pieces = models.CharField(max_length=255, null=True)
    damaged_sku_pieces = models.CharField(max_length=255, null=True)
    product_cgst = models.CharField(max_length=255, null=True)
    product_sgst = models.CharField(max_length=255, null=True)
    product_igst = models.CharField(max_length=255, null=True)
    product_cess = models.CharField(max_length=255, null=True)
    sales_person_name = models.CharField(max_length=255, null=True)
    order_type = models.CharField(max_length=255, null=True)
    campaign_name= models.CharField(max_length=255, null=True)
    discount = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return  "%s"%(self.order_invoice)

class GRNReports(models.Model):
    po_no = models.CharField(max_length=255, null=True)
    po_date = models.CharField(max_length=255, null=True)
    po_status = models.CharField(max_length=255, null=True)
    vendor_name = models.CharField(max_length=255, null=True)
    vendor_id = models.CharField(max_length=255, null=True)
    buyer_shop = models.CharField(max_length=255, null=True)
    shipping_address = models.CharField(max_length=255, null=True)
    category_manager = models.CharField(max_length=255, null=True)
    product_id = models.CharField(max_length=255, null=True)
    product_name = models.CharField(max_length=255, null=True)
    product_brand = models.CharField(max_length=255, null=True)
    manufacture_date = models.CharField(max_length=255, null=True)
    expiry_date = models.CharField(max_length=255, null=True)
    po_sku_pieces = models.CharField(max_length=255, null=True)
    product_mrp = models.CharField(max_length=255, null=True)
    discount = models.CharField(max_length=255, null=True)
    gram_to_brand_price = models.CharField(max_length=255, null=True)
    grn_id = models.CharField(max_length=255, null=True)
    grn_date = models.CharField(max_length=255, null=True)
    grn_sku_pieces = models.CharField(max_length=255, null=True)
    product_cgst = models.CharField(max_length=255, null=True)
    product_sgst = models.CharField(max_length=255, null=True)
    product_igst = models.CharField(max_length=255, null=True)
    product_cess = models.CharField(max_length=255, null=True)
    invoice_item_gross_value = models.CharField(max_length=255, null=True)
    delivered_sku_pieces = models.CharField(max_length=255, null=True)
    returned_sku_pieces= models.CharField(max_length=255, null=True)
    dn_number = models.CharField(max_length=255, null=True)
    dn_value_basic = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return  "%s"%(self.po_no)

class MasterReports(models.Model):
    product = models.CharField(max_length=255, null=True)
    service_partner = models.CharField(max_length=255, null=True)
    mrp = models.CharField(max_length=255, null=True)
    price_to_retailer = models.CharField(max_length=255, null=True)
    #New Fields Added
    selling_price = models.CharField(max_length=255, null=True)
    buyer_shop = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=255, null=True)
    pincode = models.CharField(max_length=255, null=True)
    product_gf_code = models.CharField(max_length=255, null=True)
    product_brand = models.CharField(max_length=255, null=True)
    product_subbrand = models.CharField(max_length=255, null=True)
    product_category = models.CharField(max_length=255, null=True)
    tax_gst_percentage = models.CharField(max_length=255, null=True)
    tax_cess_percentage = models.CharField(max_length=255, null=True)
    tax_surcharge_percentage = models.CharField(max_length=255, null=True)
    pack_size = models.CharField(max_length=255, null=True)
    case_size = models.CharField(max_length=255, null=True)
    hsn_code = models.CharField(max_length=255, null=True)
    product_id = models.CharField(max_length=255, null=True)
    sku_code = models.CharField(max_length=255, null=True)
    short_description = models.CharField(max_length=3000, null=True)
    long_description = models.CharField(max_length=3000, null=True)
    created_at = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return  "%s"%(self.product)

class OrderGrnReports(models.Model):
    order = models.CharField(max_length=255, null=True)
    grn = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return "%s"%(self.order)

class RetailerReports(models.Model):
    retailer_id = models.CharField(max_length=255, null=True)
    retailer_name = models.CharField(max_length=255, null=True)
    retailer_type = models.CharField(max_length=255, null=True)
    retailer_phone_number = models.CharField(max_length=255, null=True)
    created_at = models.CharField(max_length=255, null=True)
    service_partner = models.CharField(max_length=255, null=True)
    service_partner_id = models.CharField(max_length=255, null=True)
    service_partner_contact = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return  "%s"%(self.retailer_name)   


class CategoryProductReports(models.Model):
    product_id = models.CharField(max_length=255, null=True)
    product_name = models.CharField(max_length=255, null=True)
    product_short_description = models.CharField(max_length=255, null=True)
    product_created_at = models.CharField(max_length=255, null=True)
    category_id = models.CharField(max_length=255, null=True)
    category = models.CharField(max_length=255, null=True)
    category_name = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return  "%s"%(self.product_name)

class ShopStock(models.Model):
    product_id = models.CharField(max_length=255, null=True)
    available_qty = models.CharField(max_length=255, null=True)
    damage_qty = models.CharField(max_length=255, null=True)
    shop_id = models.CharField(max_length=255, null=True)
    created_at = models.CharField(max_length=255, null=True)

class TripShipmentReport(models.Model):
    shipment_id=models.CharField(max_length=255, null=True)
    trip_id=models.CharField(max_length=255, null=True)
    trip=models.CharField(max_length=255, null=True)
    shipment=models.CharField(max_length=255, null=True)
    shipment_status=models.CharField(max_length=255, null=True)
    trip_status=models.CharField(max_length=255, null=True)
    trip_created_at=models.CharField(max_length=255, null=True)
    delivery_boy=models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)

    def _str__(self):
        return "%s"%(self.trip)

class TriReport(models.Model):
    trip_id=models.CharField(max_length=255, null=True)
    seller_shop=models.CharField(max_length=255, null=True)
    dispatch_no=models.CharField(max_length=255, null=True)
    delivery_boy=models.CharField(max_length=255, null=True)
    vehicle_no=models.CharField(max_length=255, null=True)
    trip_status=models.CharField(max_length=255, null=True)
    e_way_bill_no=models.CharField(max_length=255, null=True)
    starts_at=models.CharField(max_length=255, null=True)
    completed_at=models.CharField(max_length=255, null=True)
    trip_amount=models.CharField(max_length=255, null=True)
    received_amount=models.CharField(max_length=255, null=True)
    created_at=models.CharField(max_length=255, null=True)
    modified_at=models.CharField(max_length=255, null=True)
    total_crates_shipped=models.CharField(max_length=255, null=True)
    total_packets_shipped=models.CharField(max_length=255, null=True)
    total_sacks_shipped=models.CharField(max_length=255, null=True)
    total_crates_collected=models.CharField(max_length=255, null=True)
    total_packets_collected=models.CharField(max_length=255, null=True)
    total_sacks_collected=models.CharField(max_length=255, null=True)
    cash_to_be_collected=models.CharField(max_length=255, null=True)
    cash_collected_by_delivery_boy=models.CharField(max_length=255, null=True)
    total_paid_amount=models.CharField(max_length=255, null=True)
    total_received_amount=models.CharField(max_length=255, null=True)
    received_cash_amount=models.CharField(max_length=255, null=True)
    received_online_amount=models.CharField(max_length=255, null=True)
    cash_to_be_collected_value=models.CharField(max_length=255, null=True)
    total_trip_shipments=models.CharField(max_length=255, null=True)
    total_trip_amount=models.CharField(max_length=255, null=True)
    total_trip_amount_value=models.CharField(max_length=255, null=True)
    trip_weight=models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.dispatch_no

class OrderDetailReportsData(models.Model):
    invoice_id = models.CharField(max_length=255, null=True)
    order_invoice = models.CharField(max_length=255, null=True)
    invoice_date = models.CharField(max_length=255, null=True)
    invoice_modified_at = models.CharField(max_length=255, null=True)
    invoice_last_modified_by = models.CharField(max_length=255, null=True)
    invoice_status = models.CharField(max_length=255, null=True)
    order_id = models.CharField(max_length=255, null=True)
    seller_shop = models.CharField(max_length=255, null=True)
    order_status = models.CharField(max_length=255, null=True)
    order_date = models.CharField(max_length=255, null=True)
    order_modified_at = models.CharField(max_length=255, null=True)
    order_by = models.CharField(max_length=255, null=True)
    retailer_id = models.CharField(max_length=255, null=True)
    retailer_name = models.CharField(max_length=255, null=True)
    pin_code = models.CharField(max_length=255, null=True)
    product_id = models.CharField(max_length=255, null=True)
    product_name = models.CharField(max_length=255, null=True)
    product_brand = models.CharField(max_length=255, null=True)
    product_mrp = models.CharField(max_length=255, null=True)
    product_value_tax_included = models.CharField(max_length=255, null=True)
    ordered_sku_pieces = models.CharField(max_length=255, null=True)
    shipped_sku_pieces = models.CharField(max_length=255, null=True)
    delivered_sku_pieces = models.CharField(max_length=255, null=True)
    returned_sku_pieces = models.CharField(max_length=255, null=True)
    damaged_sku_pieces = models.CharField(max_length=255, null=True)
    product_cgst = models.CharField(max_length=255, null=True)
    product_sgst = models.CharField(max_length=255, null=True)
    product_igst = models.CharField(max_length=255, null=True)
    product_cess = models.CharField(max_length=255, null=True)
    sales_person_name = models.CharField(max_length=255, null=True)
    order_type = models.CharField(max_length=255, null=True)
    campaign_name= models.CharField(max_length=255, null=True)
    discount = models.CharField(max_length=255, null=True)
    trip = models.CharField(max_length=255, null=True)
    trip_id = models.CharField(max_length=255, null=True)
    trip_status = models.CharField(max_length=255, null=True)
    delivery_boy = models.CharField(max_length=255, null=True)
    trip_created_at = models.CharField(max_length=255, null=True)
    selling_price = models.CharField(max_length=255, null=True)
    item_effective_price = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s"%(self.order_id)

class CartProductMappingData(models.Model):
    qty = models.CharField(max_length=255, null=True)
    qty_error_msg = models.CharField(max_length=255, null=True)
    created_at = models.CharField(max_length=255, null=True)
    modified_at = models.CharField(max_length=255, null=True)
    cart = models.CharField(max_length=255, null=True)
    cart_product = models.CharField(max_length=255, null=True)
    cart_product_price = models.CharField(max_length=255, null=True)
    no_of_pieces = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=255, null=True)
    event_occurred_at = models.DateTimeField(auto_now_add=True)

    def _str__(self):
        return "%s"%(self.cart)


class InventoryArchiveMaster(models.Model):
    ARCHIVE_INVENTORY_CHOICES = Choices(('WAREHOUSE', 'wms_warehouse_inventory'), ('BIN', 'wms_bin_inventory'))
    archive_date = models.DateField()
    inventory_type = models.CharField(max_length=20, choices=ARCHIVE_INVENTORY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wms_archive_inventory_master"


class WarehouseInventoryHistoric(models.Model):
    archive_entry = models.ForeignKey(InventoryArchiveMaster, null=False, on_delete=models.DO_NOTHING)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    inventory_state = models.ForeignKey(InventoryState, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    in_stock = models.BooleanField()
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wms_warehouse_inventory_history"


    
class PosInventoryHistoric(models.Model):
    product = models.ForeignKey(RetailerProduct, on_delete=models.DO_NOTHING)
    quantity = models.IntegerField(default=0)
    inventory_state = models.ForeignKey(PosInventoryState, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    # class Meta:
    #     db_table = "pos_inventory_history"

class BinInventoryHistoric(models.Model):
    archive_entry = models.ForeignKey(InventoryArchiveMaster, null=False, on_delete=models.DO_NOTHING)
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    batch_id = models.CharField(max_length=50, null=True, blank=True)
    inventory_type = models.ForeignKey(InventoryType, null=True, blank=True, on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    in_stock = models.BooleanField()
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wms_bin_inventory_history"


class CronRunLog(models.Model):
    CRON_CHOICE = Choices(('PICKUP_CREATION_CRON', 'Picklist Generation Cron'),
                          ('AUDIT_PICKUP_REFRESH_CRON', 'Refresh Picklist After Audit Cron'),
                          ('FRANCHISE_SALES_RETURNS_CRON', 'Adjust Sales/Returns Franchise Inventory Cron'),
                          ('HDPOS_USERS_FETCH_CRON', 'Fetch Registered Customers on Hdpos'),
                          ('MARKETING_REWARDS_NOTIFY', 'Notify users about rewards'),
                          ('AUTO_ORDER_PROCESSING_CRON', 'Auto Order Processing'),
                          ('SCHEME_EXPIRY_CRON', 'Deactivate expired schemes and mappings'),
                          ('ARS_CRON', 'ARS Cron'),
                          ('PO_CREATION_CRON', 'PO creation Cron'),)

    CRON_STATUS_CHOICES = Choices((0, 'STARTED', 'Started'),
                                  (1, 'ABORTED', 'Aborted'),
                                  (2, 'COMPLETED', 'Completed'))
    cron_name = models.CharField(choices=CRON_CHOICE, max_length=50)
    status = models.PositiveSmallIntegerField(choices=CRON_STATUS_CHOICES, default=CRON_STATUS_CHOICES.STARTED)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True)
