from django.contrib import admin
from .models import RetailerReports, OrderReports, GRNReports, MasterReports, OrderGrnReports, OrderDetailReportsData,CategoryProductReports, TripShipmentReport, TriReport
# Register your models here.

class OrderDetailReportsDataAdmin(admin.ModelAdmin):
    list_display = '__all__'
admin.site.register(OrderDetailReportsData, OrderDetailReportsDataAdmin)

class OrderReportsAdmin(admin.ModelAdmin):
    list_display = ('order_invoice', 'invoice_date', 'invoice_status', 'order_id', 'seller_shop',  'order_status', 'order_date', 'order_by', 'retailer_id', 'retailer_name', 'pin_code', 'product_id', 'product_name', 'product_brand', 'product_mrp', 'product_value_tax_included', 'ordered_sku_pieces', 'shipped_sku_pieces', 'delivered_sku_pieces', 'returned_sku_pieces', 'damaged_sku_pieces', 'product_cgst', 'product_sgst', 'product_igst', 'product_cess', 'sales_person_name', 'order_type', 'campaign_name', 'discount')

admin.site.register(OrderReports, OrderReportsAdmin)

class GRNReportsAdmin(admin.ModelAdmin):
    list_display = '__all_'

admin.site.register(GRNReports, GRNReportsAdmin)

class MasterReportsAdmin(admin.ModelAdmin):
    list_display = '__all__'

admin.site.register(MasterReports, MasterReportsAdmin)

class OrderGrnReportsAdmin(admin.ModelAdmin):
    list_display = ('order', 'grn')
admin.site.register(OrderGrnReports, OrderGrnReportsAdmin)

class RetailerReportsAdmin(admin.ModelAdmin):
    list_display ='__all__'
admin.site.register(RetailerReports, RetailerReportsAdmin) 

class CategoryProductReportsAdmin(admin.ModelAdmin):
    list_display = '__all__'
admin.site.register(CategoryProductReports, CategoryProductReportsAdmin)

class TripShipmentReportAdmin(admin.ModelAdmin):
    list_display = '__all__'
admin.site.register(TripShipmentReport, TripShipmentReportAdmin)

class TriReportAdmin(admin.ModelAdmin):
    list_display = '__all__'
admin.site.register(TriReport, TriReportAdmin)







