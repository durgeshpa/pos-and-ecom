from django.db import models

# Create your models here.
class OrderReports(models.Model):
    order_invoice = models.CharField(max_length=255, null=True)
    invoice_date = models.CharField(max_length=255, null=True)
    invoice_status = models.CharField(max_length=255, null=True)
    order_id = models.CharField(max_length=255, null=True)
    seller_shop = models.CharField(max_length=255, null=True)
    order_status = models.CharField(max_length=255, null=True)
    order_date = models.CharField(max_length=255, null=True)
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


    def __str__(self):
        return  "%s"%(self.po_no)

class MasterReports(models.Model):
    product = models.CharField(max_length=255, null=True)
    service_partner = models.CharField(max_length=255, null=True)
    mrp = models.CharField(max_length=255, null=True)
    price_to_retailer = models.CharField(max_length=255, null=True)
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


    def __str__(self):
        return  "%s"%(self.product)

class OrderGrnReports(models.Model):
    order = models.CharField(max_length=255, null=True)
    grn = models.CharField(max_length=255, null=True)

    def __str__(self):
        return  "%s"%(self.order)
