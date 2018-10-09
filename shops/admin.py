from django.contrib import admin
from .models import Shop,ShopType,RetailerType,SpRetailerMapping

class ShopAdmin(admin.ModelAdmin):
    list_display = ('shop_name','shop_owner','shop_type','status')


admin.site.register(SpRetailerMapping)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
