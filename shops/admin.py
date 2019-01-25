from django.contrib import admin
from .models import Shop,ShopType,RetailerType,ParentRetailerMapping,ShopPhoto,ShopDocument
from addresses.models import Address
from .forms import ParentRetailerMappingForm
from retailer_backend.admin import InputFilter
from django.db.models import Q

class ShopTypeSearch(InputFilter):
    parameter_name = 'shop_type'
    title = 'Shop Type'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_type = self.value()
            if shop_type is None:
                return
            return queryset.filter(
                Q(shop_type__shop_type__icontains=shop_type)
            )

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
    list_display = ('shop_name','shop_owner','shop_type','status', 'get_shop_city')
    filter_horizontal = ('related_users',)
    list_filter = (ShopTypeSearch,)

    # def get_shop_pending_amount(self, obj):
    #     pending_amount_gf = 0
    #     pending_amount_sp = 0
    #     pending_amount_total=0
    #     if obj.shop_type.shop_type == 'r':
    #         #if obj.retiler_mapping.filter(status=True).last().parent.shop_type.shop_type=='gf':
    #         orders_to_gf = obj.rtg_buyer_shop_order.all()
    #         for order in orders_to_gf:
    #             if order.rt_payment.last().payment_status == 'payment_done_approval_pending' or order.rt_payment.last().payment_status == 'cash_collected':
    #                 pending_amount_gf = pending_amount_gf + order.total_final_amount
    #         #return pending_amount
    #         #elif obj.retiler_mapping.filter(status=True).last().parent.shop_type.shop_type=='sp':
    #         orders_to_sp = obj.rt_buyer_shop_order.all()
    #         for order in orders_to_sp:
    #             if order.rt_payment.last().payment_status == 'payment_done_approval_pending' or order.rt_payment.last().payment_status == 'cash_collected':
    #                 pending_amount_sp = pending_amount_sp + order.total_final_amount
    #         #return pending_amount
    #         pending_amount_total = pending_amount_gf + pending_amount_sp
    #         return pending_amount_total
    #     elif obj.shop_type.shop_type == 'sp':
    #         carts_to_gf = obj.sp_shop_cart.all()
    #         total_pending_amount = 0
    #         for cart in carts_to_gf:
    #             for order in cart.sp_order_cart_mapping.all():
    #                 total_pending_amount = total_pending_amount + order.total_final_amount
    #         return total_pending_amount
    # get_shop_pending_amount.short_description = 'Shop Pending Amount'

    def get_shop_city(self, obj):
        if obj.shop_name_address_mapping.exists():
            return obj.shop_name_address_mapping.last().city
    get_shop_city.short_description = 'Shop City'

class ParentRetailerMappingAdmin(admin.ModelAdmin):
    form = ParentRetailerMappingForm

admin.site.register(ParentRetailerMapping,ParentRetailerMappingAdmin)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
