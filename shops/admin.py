from django.contrib import admin
from .models import (
    Shop, ShopType, RetailerType, ParentRetailerMapping,
    ShopPhoto, ShopDocument, ShopInvoicePattern
)
from addresses.models import Address
from .forms import ParentRetailerMappingForm
from retailer_backend.admin import InputFilter
from django.db.models import Q
from django.utils.html import format_html

class ShopTypeSearch(InputFilter):
    parameter_name = 'shop_type'
    title = 'Shop Type'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_type = self.value()
            if shop_type is None:
                return
            return queryset.filter(shop_type__shop_type__icontains=shop_type)

class ShopRelatedUserSearch(InputFilter):
    parameter_name = 'related_users'
    title = 'Related User'

    def queryset(self, request, queryset):
        if self.value() is not None:
            related_user_number = self.value()
            if related_user_number is None:
                return
            return queryset.filter(related_users__phone_number__icontains=related_user_number)

class ShopOwnerSearch(InputFilter):
    parameter_name = 'shop_owner'
    title = 'Shop Owner'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_owner_number = self.value()
            if shop_owner_number is None:
                return
            return queryset.filter(shop_owner__phone_number__icontains=shop_owner_number)

class ShopPhotosAdmin(admin.TabularInline):
    model = ShopPhoto
    fields = ( 'shop_photo','shop_photo_thumbnail', )
    readonly_fields = ('shop_photo_thumbnail',)
    extra = 2

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
    extra = 2


class ShopInvoicePatternAdmin(admin.TabularInline):
    model = ShopInvoicePattern
    extra = 1
    fields = ('pattern', 'status')


class AddressAdmin(admin.TabularInline):
    model = Address
    fields = ('address_contact_name','address_contact_number','address_type','address_line1','state','city','pincode',)
    extra = 2

class ShopAdmin(admin.ModelAdmin):
    inlines = [
        ShopPhotosAdmin, ShopDocumentsAdmin,
        AddressAdmin, ShopInvoicePatternAdmin
    ]
    list_display = ('shop_name','shop_owner','shop_type','status', 'get_shop_city','shop_mapped_product')
    filter_horizontal = ('related_users',)
    list_filter = (ShopTypeSearch,ShopRelatedUserSearch,ShopOwnerSearch,)
    search_fields = ('shop_name',)

    def get_queryset(self, request):
        qs = super(ShopAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.has_perm('shops.can_see_all_shops'):
            return qs
        return qs.filter(
            Q(related_users=request.user) |
            Q(shop_owner=request.user)
        )

    def shop_mapped_product(self, obj):
        if obj.shop_type.shop_type in ['gf','sp']:
            return format_html("<a href = '/admin/shops/shop-mapped/%s/product/' class ='addlink' > Product List</a>"% (obj.id))

    shop_mapped_product.short_description = 'Product List with Qty'


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
