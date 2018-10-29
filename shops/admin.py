from django.contrib import admin
from .models import Shop,ShopType,RetailerType,SpRetailerMapping,ShopPhoto, \
                    ShopDocument

class ShopPhotosAdmin(admin.TabularInline):
    model = ShopPhoto
    fields = ( 'shop_photo','shop_photo_thumbnail', )
    readonly_fields = ('shop_photo_thumbnail',)

class ShopDocumentsAdmin(admin.TabularInline):
    model = ShopDocument
    fields = ( 'shop_document_type','shop_document_number','shop_document_photo','shop_document_photo_thumbnail', )
    readonly_fields = ('shop_document_photo_thumbnail',)

class ShopAdmin(admin.ModelAdmin):
    inlines = [ShopPhotosAdmin, ShopDocumentsAdmin]
    list_display = ('shop_name','shop_owner','shop_type','status')

admin.site.register(SpRetailerMapping)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
