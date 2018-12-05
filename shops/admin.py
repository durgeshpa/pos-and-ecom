from django.contrib import admin
from .models import Shop,ShopType,RetailerType,ParentRetailerMapping,ShopPhoto,ShopDocument
from addresses.models import Address
from .forms import ParentRetailerMappingForm
class ShopPhotosAdmin(admin.TabularInline):
    model = ShopPhoto
    fields = ( 'shop_photo','shop_photo_thumbnail', )
    readonly_fields = ('shop_photo_thumbnail',)

class ShopDocumentsAdmin(admin.TabularInline):
    model = ShopDocument
    fields = ( 'shop_document_type','shop_document_number','shop_document_photo','shop_document_photo_thumbnail', )
    readonly_fields = ('shop_document_photo_thumbnail',)

class AddressAdmin(admin.TabularInline):
    model = Address
    fields = ('address_contact_name','address_contact_number','address_type','address_line1','state','city','pincode',)

class ShopAdmin(admin.ModelAdmin):
    inlines = [ShopPhotosAdmin, ShopDocumentsAdmin,AddressAdmin]
    list_display = ('shop_name','shop_owner','shop_type','status')

class ParentRetailerMappingAdmin(admin.ModelAdmin):
    form = ParentRetailerMappingForm
    
admin.site.register(ParentRetailerMapping,ParentRetailerMappingAdmin)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
