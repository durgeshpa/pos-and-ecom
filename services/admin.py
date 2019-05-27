from django.contrib import admin
from .models import OrderReports, GRNReports
# Register your models here.
class OrderReportsAdmin(admin.ModelAdmin):
    list_display = ('order_invoice', 'invoice_date', 'invoice_status', 'order_id',  'order_status', 'order_date', 'order_by', 'retailer_id', 'pin_code', 'product_id', 'product_name', 'product_brand', 'product_mrp', 'product_value_tax_included', 'ordered_sku_pieces', 'shipped_sku_pieces', 'delivered_sku_pieces', 'returned_sku_pieces', 'damaged_sku_pieces', 'product_cgst', 'product_sgst', 'product_igst', 'product_cess', 'sales_person_name', 'order_type', 'campaign_name', 'discount')

admin.site.register(OrderReports, OrderReportsAdmin)

class GRNReportsAdmin(admin.ModelAdmin):
    list_display = ('po_no', 'po_date', 'po_status', 'vendor_name',  'vendor_id', 'shipping_address', 'category_manager', 'product_id', 'product_name', 'product_brand', 'manufacture_date', 'expiry_date', 'po_sku_pieces', 'product_mrp', 'discount', 'gram_to_brand_price', 'grn_id', 'grn_date', 'grn_sku_pieces', 'product_cgst', 'product_sgst', 'product_igst', 'product_cess', 'invoice_item_gross_value', 'delivered_sku_pieces', 'returned_sku_pieces', 'dn_number', 'dn_value_basic')

admin.site.register(GRNReports, GRNReportsAdmin)
