from django.contrib import admin
from pos.models import RetailerProduct, RetailerProductImage


# Register your models here.

class RetailerProductAdmin(admin.ModelAdmin):
    list_display = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code', 'linked_product', 'description',
                    'sku_type', 'status', 'created_at', 'modified_at')
    fields = ('shop', 'linked_product', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
              'description', 'sku_type', 'status', 'created_at', 'modified_at')
    readonly_fields = ('shop', 'linked_product', 'sku_type', 'created_at', 'modified_at')
    list_per_page = 50

admin.site.register(RetailerProduct, RetailerProductAdmin)
admin.site.register(RetailerProductImage)
