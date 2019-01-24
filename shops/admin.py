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
    list_display = ('shop_name','shop_owner','shop_type','status', 'get_shop_pending_amount')
    filter_horizontal = ('related_users',)

    def get_shop_pending_amount(self, obj):
        if obj.shop_type.shop_type == 'r':
            if obj.retiler_mapping.filter(status=True).last().parent.shop_type.shop_type=='gf':
                orders = obj.rtg_buyer_shop_order.all()
                pending_amount = 0
                for order in orders:
                    if order.rt_payment.last().payment_status == 'payment_done_approval_pending' or order.rt_payment.last().payment_status == 'cash_collected':
                        pending_amount = pending_amount + order.total_final_amount
                return pending_amount
            elif obj.retiler_mapping.filter(status=True).last().parent.shop_type.shop_type=='sp':
                orders = obj.rt_buyer_shop_order.all()
                pending_amount = 0
                for order in orders:
                    if order.rt_payment.last().payment_status == 'payment_done_approval_pending' or order.rt_payment.last().payment_status == 'cash_collected':
                        pending_amount = pending_amount + order.total_final_amount
                return pending_amount
    get_shop_pending_amount.short_description = 'Shop Pending Amount'


class ParentRetailerMappingAdmin(admin.ModelAdmin):
    form = ParentRetailerMappingForm

admin.site.register(ParentRetailerMapping,ParentRetailerMappingAdmin)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
