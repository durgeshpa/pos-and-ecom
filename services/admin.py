from django.contrib import admin
from .models import OrderReports
# Register your models here.
class OrderReportsAdmin(admin.ModelAdmin):
    list_display = ('order_invoice', 'invoice_date', 'invoice_status', 'order_id',  'order_status', 'order_date', 'order_by', 'retailer_id', 'pin_code', 'product_id', 'product_name', 'product_brand', 'product_mrp', 'product_value_tax_included', 'ordered_sku_pieces', 'shipped_sku_pieces', 'delivered_sku_pieces', 'returned_sku_pieces', 'damaged_sku_pieces', 'product_cgst', 'product_sgst', 'product_igst', 'product_cess', 'sales_person_name', 'order_type', 'campaign_name', 'discount')

admin.site.register(OrderReports, OrderReportsAdmin)
