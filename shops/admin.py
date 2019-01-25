from django.contrib import admin
from .models import Shop,ShopType,RetailerType,ParentRetailerMapping,ShopPhoto,ShopDocument
from addresses.models import Address
from .forms import ParentRetailerMappingForm
class ShopPhotosAdmin(admin.TabularInline):
    model = ShopPhoto
    fields = ( 'shop_photo','shop_photo_thumbnail', )
    readonly_fields = ('shop_photo_thumbnail',)

from django.forms.models import BaseInlineFormSet
class RequiredInlineFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        form = super(RequiredInlineFormSet, self)._construct_form(i, **kwargs)
        if i < 1:
            form.empty_permitted = False
        return form

class ShopDocumentsAdmin(admin.TabularInline):
    model = ShopDocument
    fields = ( 'shop_document_type','shop_document_number','shop_document_photo','shop_document_photo_thumbnail', )
    readonly_fields = ('shop_document_photo_thumbnail',)
    formset = RequiredInlineFormSet

class AddressAdmin(admin.TabularInline):
    model = Address
    fields = ('address_contact_name','address_contact_number','address_type','address_line1','state','city','pincode',)

class ShopAdmin(admin.ModelAdmin):
    inlines = [ShopPhotosAdmin, ShopDocumentsAdmin,AddressAdmin]
    list_display = ('shop_name','shop_owner','shop_type','status')
    filter_horizontal = ('related_users',)

class ParentRetailerMappingAdmin(admin.ModelAdmin):
    form = ParentRetailerMappingForm
    
admin.site.register(ParentRetailerMapping,ParentRetailerMappingAdmin)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
