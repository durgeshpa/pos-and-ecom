import csv

from django.contrib import admin
from .models import (
    Shop, ShopType, RetailerType, ParentRetailerMapping,
    ShopPhoto, ShopDocument, ShopInvoicePattern, FavouriteProduct,
)
from addresses.models import Address
from .forms import (ParentRetailerMappingForm, ShopParentRetailerMappingForm,
                    ShopForm, AddressForm, RequiredInlineFormSet,
                    AddressInlineFormSet)
from .views import (StockAdjustmentView, stock_adjust_sample,
                    bulk_shop_updation)
from retailer_backend.admin import InputFilter
from django.db.models import Q
from django.utils.html import format_html
from import_export import resources
from django.http import HttpResponse
from admin_auto_filters.filters import AutocompleteFilter
from services.views import SalesReportFormView, SalesReport
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from .utils import create_shops_excel


class ShopResource(resources.ModelResource):
    class Meta:
        model = Shop
        exclude = ('created_at','modified_at')


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        return create_shops_excel(queryset)

    export_as_csv.short_description = "Download CSV of Selected Shops"

    def export_as_csv_fav_product(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['modified_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        return response
    export_as_csv_fav_product.short_description = "Download CSV of Selected Objects"


class ShopNameSearch(InputFilter):
    parameter_name = 'shop_name'
    title = 'Shop Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_name = self.value()
            if shop_name is None:
                return
            return queryset.filter(shop_name__icontains=shop_name)

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

class ShopFilter(AutocompleteFilter):
    title = 'Shop' # display title
    field_name = 'buyer_shop' # name of the foreign key field


class ProductFilter(AutocompleteFilter):
    title = 'Product' # display title
    field_name = 'product' # name of the foreign key field    


class FavouriteProductAdmin(admin.ModelAdmin, ExportCsvMixin):
    #change_list_template = 'admin/shops/shop/change_list.html'
    actions = ["export_as_csv_fav_product"]
    list_display = ('buyer_shop', 'product', 'created_at', 'get_product_brand')#, 'get_product_sp')
    raw_id_fields = ['buyer_shop', 'product']
    list_filter = (ShopFilter, ProductFilter)

    # def get_product_sp(self, obj):
    #     return obj.product.product_brand
    # get_product_sp.short_description = 'Parent Shop Name'  #Renames column head


    def get_product_brand(self, obj):
        return obj.product.product_brand
    get_product_brand.short_description = 'Brand Name'  #Renames column head

    class Media:
        pass


class ShopPhotosAdmin(admin.TabularInline):
    model = ShopPhoto
    fields = ( 'shop_photo','shop_photo_thumbnail', )
    readonly_fields = ('shop_photo_thumbnail',)
    formset = RequiredInlineFormSet
    extra = 2

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
    formset = AddressInlineFormSet
    form = AddressForm
    fields = ('nick_name','address_contact_name','address_contact_number','address_type','address_line1','state','city','pincode',)
    extra = 2

class ShopParentRetailerMapping(admin.TabularInline):
    model = ParentRetailerMapping
    form = ShopParentRetailerMappingForm
    fields = ('parent',)
    fk_name = 'retailer'
    extra = 1
    max_num = 1

class ServicePartnerFilter(InputFilter):
    title = 'Service Partner'
    parameter_name = 'service partner'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(retiler_mapping__parent__shop_name__icontains=value )
        return queryset

class ShopCityFilter(InputFilter):
    title = 'City'
    parameter_name = 'city'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(shop_name_address_mapping__city__city_name__icontains=value, shop_name_address_mapping__address_type='shipping')
        return queryset

class ShopAdmin(admin.ModelAdmin, ExportCsvMixin):
    change_list_template = 'admin/shops/shop/change_list.html'
    resource_class = ShopResource
    form = ShopForm
    actions = ["export_as_csv"]
    inlines = [
        ShopPhotosAdmin, ShopDocumentsAdmin,
        AddressAdmin, ShopInvoicePatternAdmin,ShopParentRetailerMapping
    ]
    list_display = ('shop_name', 'get_shop_shipping_address', 'get_shop_pin_code', 'get_shop_parent','shop_owner','shop_type','created_at','status', 'get_shop_city','shop_mapped_product','imei_no',)
    filter_horizontal = ('related_users',)
    list_filter = (ShopCityFilter,ServicePartnerFilter,ShopNameSearch,ShopTypeSearch,ShopRelatedUserSearch,ShopOwnerSearch,'status',('created_at', DateTimeRangeFilter))
    search_fields = ('shop_name', )
    list_per_page = 50

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ShopAdmin, self).get_urls()
        urls = [
            url(
                r'^adjust-stock/(?P<shop_id>\w+)/$',
                self.admin_site.admin_view(StockAdjustmentView.as_view()),
                name="StockAdjustment"
            ),
            url(
                r'^adjust-stock-sample/(?P<shop_id>\w+)/$',
                self.admin_site.admin_view(stock_adjust_sample),
                name="ShopStocks"
            ),
            url(
                r'^shop-sales-report/$',
                self.admin_site.admin_view(SalesReport.as_view()),
                name="shop-sales-report"
            ),
            url(
                r'^shop-sales-form/$',
                self.admin_site.admin_view(SalesReportFormView.as_view()),
                name="shop-sales-form"
            ),
            url(
                r'^bulk-shop-updation/$',
                self.admin_site.admin_view(bulk_shop_updation),
                name="bulk-shop-updation"
            ),
        ] + urls
        return urls


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

class ParentFilter(AutocompleteFilter):
    title = 'Parent' # display title
    field_name = 'parent' # name of the foreign key field

class RetailerFilter(AutocompleteFilter):
    title = 'Retailer' # display title
    field_name = 'retailer' # name of the foreign key field

class ParentRetailerMappingAdmin(admin.ModelAdmin):
    form = ParentRetailerMappingForm
    list_filter = (ParentFilter,RetailerFilter,'status')

    class Media:
        pass

admin.site.register(ParentRetailerMapping,ParentRetailerMappingAdmin)
admin.site.register(ShopType)
admin.site.register(RetailerType)
admin.site.register(Shop,ShopAdmin)
admin.site.register(FavouriteProduct, FavouriteProductAdmin)