from django.contrib import admin
from pos.models import RetailerProduct, RetailerProductImage


# Register your models here.

class RetailerProductAdmin(admin.ModelAdmin):
    list_display = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'linked_product', 'description', 'sku_type', 'status', 'created_at', 'modified_at')
    fields = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'linked_product', 'description', 'sku_type', 'status', 'created_at', 'modified_at')
    readonly_fields = ('created_at', 'modified_at')
    list_per_page = 50

admin.site.register(RetailerProduct, RetailerProductAdmin)
admin.site.register(RetailerProductImage)
