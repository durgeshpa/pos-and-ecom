from django.contrib import admin
from pos.models import RetailerProduct


# Register your models here.

class RetailerProductAdmin(admin.ModelAdmin):
    list_display = (
        'shop', 'sku', 'name', 'mrp', 'selling_price', 'linked_product', 'description', 'sku_type', 'status',
        'created_at',
        'modified_at')


admin.site.register(RetailerProduct, RetailerProductAdmin)
