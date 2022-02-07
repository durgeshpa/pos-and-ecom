import csv
from datetime import date
from io import StringIO
from django.db.models import Q, Sum
from django.contrib import admin
from django.conf.urls import url
from django.db.models import Q
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django_admin_listfilter_dropdown.filters import RelatedOnlyDropdownFilter
from rangefilter.filter import DateRangeFilter
from dal_admin_filters import AutocompleteFilter
from rangefilter.filter import DateTimeRangeFilter

from accounts.middlewares import get_current_user

from marketing.filters import UserFilter, PosBuyerFilter
from coupon.admin import CouponCodeFilter, CouponNameFilter, RuleNameFilter
from retailer_to_sp.admin import OrderIDFilter, SellerShopFilter
from wms.models import PosInventory, PosInventoryChange, PosInventoryState
from .common_functions import RetailerProductCls, PosInventoryCls

from .models import (RetailerProduct, RetailerProductImage, Payment, ShopCustomerMap, Vendor, PosCart,
                     PosCartProductMapping, PosGRNOrder, PosGRNOrderProductMapping, PaymentType, ProductChange,
                     ProductChangeFields, DiscountedRetailerProduct, RetailerOrderedProduct, RetailerCoupon,
                     RetailerCouponRuleSet, RetailerRuleSetProductMapping, RetailerOrderedProductMapping, RetailerCart,
                     RetailerCartProductMapping, RetailerOrderReturn, RetailerReturnItems, InventoryPos,
                     InventoryChangePos, InventoryStatePos, MeasurementCategory, MeasurementUnit, PosReturnGRNOrder,
                     PosReturnItems, RetailerOrderedReport, BulkRetailerProduct, PaymentReconsile, RetailerOrderCancel)
from .views import upload_retailer_products_list, download_retailer_products_list_form_view, \
    DownloadRetailerCatalogue, RetailerCatalogueSampleFile, RetailerProductMultiImageUpload, DownloadPurchaseOrder, \
    download_discounted_products_form_view, download_discounted_products, \
    download_posinventorychange_products_form_view, \
    download_posinventorychange_products, get_product_details, RetailerProductStockDownload, stock_update, \
    update_retailer_product_stock, RetailerOrderedReportView, RetailerOrderedReportFormView, RetailerReturnReportFormView, \
    RetailerOrderProductInvoiceView, \
    RetailerOrderReturnCreditNoteView, posinventorychange_data_excel, RetailerPurchaseReportView, \
    RetailerPurchaseReportFormView, products_list_status, RetailerReturnReportView
from retailer_to_sp.models import Order, RoundAmount
from shops.models import Shop
from .filters import ShopFilter, ProductInvEanSearch, ProductEanSearch
from .utils import (create_order_data_excel, create_order_return_excel, create_cancel_order_csv ,\
    generate_prn_csv_report, generate_csv_payment_report, download_grn_cvs)
from .forms import RetailerProductsForm, DiscountedRetailerProductsForm, PosInventoryChangeCSVDownloadForm,\
    MeasurementUnitFormSet
from retailer_to_sp.models import Order

class ExportCsvMixin:

    def export_as_csv(self, request, queryset):
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

    export_as_csv.short_description = "Download CSV of Selected Objects"

    def export_order_return_as_csv(self, request, queryset):
        return create_order_return_excel(queryset)

    export_as_csv.short_description = "Download CSV of Selected Order Return"


class RetailerProductImageTabularAdmin(admin.TabularInline):
    model = RetailerProductImage
    fields = ('image', 'image_thumbnail',)
    readonly_fields = ('image', 'image_thumbnail',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RetailerProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')
    list_per_page = 10
    search_fields = ('product__name',)

    def get_queryset(self, request):
        qs = super(RetailerProductImageAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__shop__pos_shop__user=request.user,
                         product__shop__pos_shop__status=True)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RetailerProductAdmin(admin.ModelAdmin):
    change_list_template = 'admin/pos/pos_change_list.html'
    change_form_template = 'admin/pos/pos_change_form.html'
    form = RetailerProductsForm
    list_display = ('id', 'shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code', 'image',
                    'linked_product', 'description', 'sku_type', 'status', 'product_pack_type', 'created_at',
                    'modified_at')
    fields = ('shop', 'linked_product', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
              'description', 'sku_type', 'status', 'is_deleted', 'purchase_pack_size', 'initial_purchase_value',
              'online_enabled', 'online_price', 'created_at', 'modified_at','product_pack_type','measurement_category')
    readonly_fields = ('shop', 'sku', 'product_ean_code',
                       'purchase_pack_size', 'online_enabled', 'online_price', 'name', 'created_at',
                       'sku_type', 'mrp', 'modified_at', 'description', 'initial_purchase_value')

    def get_queryset(self, request):
        qs = super(RetailerProductAdmin, self).get_queryset(request)
        qs = qs.filter(~Q(sku_type=4))
        if request.user.is_superuser:
            return qs
        return qs.filter(shop__pos_shop__user=request.user,
                         shop__pos_shop__status=True)

    list_per_page = 50
    search_fields = ('name', 'product_ean_code')
    list_filter = [ProductEanSearch, ShopFilter]
    inlines = [RetailerProductImageTabularAdmin]

    @staticmethod
    def image(obj):
        image = obj.retailer_product_image.last()
        if image:
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                image.image.url, (image.image_alt_text or image.image_name), image.image.url))

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj.linked_product:
            return self.readonly_fields + ('linked_product',)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super(RetailerProductAdmin, self).get_urls()
        urls = [
                   url(r'retailer_products_csv_download_form',
                       self.admin_site.admin_view(download_retailer_products_list_form_view),
                       name="retailer_products_csv_download_form"),

                   url(r'retailer_products_csv_download',
                       self.admin_site.admin_view(DownloadRetailerCatalogue),
                       name="retailer_products_csv_download"),

                   url(r'retailer_products_csv_upload',
                       self.admin_site.admin_view(upload_retailer_products_list),
                       name="retailer_products_csv_upload"),

                   url(r'download_sample_file',
                       self.admin_site.admin_view(RetailerCatalogueSampleFile),
                       name="download_sample_file"),

                   url(r'^retailer_product_multiple_images_upload/$',
                       self.admin_site.admin_view(RetailerProductMultiImageUpload.as_view()),
                       name='retailer_product_multiple_images_upload'),

                   url(
                       r'^retailer-purchase-value-report/$',
                       self.admin_site.admin_view(RetailerPurchaseReportView.as_view()),
                       name="retailer-purchase-value-report"
                   ),
                   url(
                      r'^retailer-purchase-value-form/$',
                      self.admin_site.admin_view(RetailerPurchaseReportFormView.as_view()),
                      name="retailer-purchase-value-form"
                   ),
                   url(
                       r'^products-list-status/(?P<product_status_info>(.*))/$',
                       self.admin_site.admin_view(products_list_status),
                       name='products-list-status'
                   ),
               ] + urls
        return urls

    class Media:
        pass


class PaymentAdmin(admin.ModelAdmin):
    list_display = ( 'order', 'order_status', 'seller_shop', 'payment_type', 'transaction_id', 'amount', 'paid_by', 'processed_by', 'created_at')
    list_per_page = 10
    search_fields = ('order__order_no', 'paid_by__phone_number', 'order__seller_shop__shop_name')
    list_filter = [('order__seller_shop', RelatedOnlyDropdownFilter),
                   ('payment_type', RelatedOnlyDropdownFilter),
                   ('created_at', DateRangeFilter)]
    actions = ['download_payment_report']

    def get_queryset(self, request):
        qs = super(PaymentAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(order__seller_shop__pos_shop__user=request.user,
                         order__seller_shop__pos_shop__status=True)

    def order_status(self, obj):
        return str(obj.order.order_status).capitalize()

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def seller_shop(self, obj):
        return obj.order.seller_shop

    def download_payment_report(self, request, queryset):
        return generate_csv_payment_report(queryset)

    class Media:
        pass


class ShopCustomerMapAdmin(admin.ModelAdmin):
    list_display = ('shop', 'user')
    list_filter = [UserFilter, ShopFilter]
    list_per_page = 10

    def get_queryset(self, request):
        qs = super(ShopCustomerMapAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(shop__pos_shop__user=request.user,
                         shop__pos_shop__status=True)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class RetailerCouponRuleSetAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super(RetailerCouponRuleSetAdmin, self).get_queryset(request)
        qs = qs.filter(coupon_ruleset__shop__shop_type__shop_type='f')
        if request.user.is_superuser:
            return qs
        return qs.filter(coupon_ruleset__shop__pos_shop__user=request.user,
                         coupon_ruleset__shop__pos_shop__status=True)

    search_fields = ('rulename', 'free_product__name', 'cart_qualifying_min_sku_value')
    list_per_page = 10
    fields = ('rulename', 'discount', 'free_product', 'free_product_qty', 'cart_qualifying_min_sku_value',
              'is_active', 'created_at', 'expiry_date')
    list_display = ('rulename', 'discount', 'free_product', 'free_product_qty', 'cart_qualifying_min_sku_value',
                    'is_active', 'created_at', 'expiry_date')
    list_filter = [RuleNameFilter, 'is_active', ('created_at', DateRangeFilter), ('expiry_date', DateRangeFilter)]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class RetailerCouponAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super(RetailerCouponAdmin, self).get_queryset(request)
        qs = qs.filter(shop__shop_type__shop_type='f')
        if request.user.is_superuser:
            return qs
        return qs.filter(shop__pos_shop__user=request.user,
                         shop__pos_shop__status=True)

    fields = ('rule', 'coupon_code', 'coupon_name', 'coupon_type', 'is_active', 'created_at', 'expiry_date')
    list_display = ('rule', 'coupon_code', 'coupon_name', 'coupon_type', 'is_active', 'created_at', 'expiry_date')
    list_filter = (CouponCodeFilter, CouponNameFilter, 'coupon_type', 'is_active')
    list_per_page = 10

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class RetailerRuleSetProductMappingAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super(RetailerRuleSetProductMappingAdmin, self).get_queryset(request)
        qs = qs.filter(rule__coupon_ruleset__shop__shop_type__shop_type='f')
        if request.user.is_superuser:
            return qs
        return qs.filter(rule__coupon_ruleset__shop__pos_shop__user=request.user,
                         rule__coupon_ruleset__shop__pos_shop__status=True)

    list_per_page = 10
    search_fields = ('rule__rulename', 'retailer_primary_product__name', 'retailer_free_product__name')
    fields = ('rule', 'combo_offer_name', 'retailer_primary_product', 'retailer_free_product',
              'purchased_product_qty', 'free_product_qty', 'is_active', 'created_at', 'expiry_date')
    list_display = ('rule', 'combo_offer_name', 'retailer_primary_product', 'retailer_free_product',
                    'purchased_product_qty', 'free_product_qty', 'is_active', 'created_at', 'expiry_date')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class RetailerCartProductMappingAdmin(admin.TabularInline):
    model = RetailerCartProductMapping
    fields = ('cart', 'retailer_product', 'qty', 'product_type', 'selling_price')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class RetailerCartAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super(RetailerCartAdmin, self).get_queryset(request)
        qs = qs.filter(cart_type='BASIC')
        if request.user.is_superuser:
            return qs
        return qs.filter(seller_shop__pos_shop__user=request.user,
                         seller_shop__pos_shop__status=True)

    list_per_page = 10
    inlines = [RetailerCartProductMappingAdmin]
    fields = ('cart_no', 'cart_status', 'order_id', 'seller_shop', 'buyer', 'offers', 'redeem_points', 'redeem_factor',
              'created_at')
    list_display = ('cart_no', 'cart_status', 'order_id', 'seller_shop', 'buyer', 'created_at')
    list_filter = (SellerShopFilter, OrderIDFilter, PosBuyerFilter)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class OrderedProductMappingInline(admin.TabularInline):
    model = RetailerOrderedProductMapping
    fields = ('retailer_product', 'qty', 'product_type', 'selling_price')
    readonly_fields = ('qty',)

    def qty(self, obj):
        return obj.shipped_qty

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class RetailerOrderProductAdmin(admin.ModelAdmin):
    inlines = (OrderedProductMappingInline,)
    search_fields = ('invoice__invoice_no', 'order__order_no', 'order__buyer__phone_number')
    list_per_page = 50
    list_display = ('order', 'invoice_no', 'download_invoice', 'order_amount', 'payment_type', 'transaction_id', 'created_at')
    actions = ["order_data_excel_action"]
    list_filter = [('order__seller_shop__shop_type', RelatedOnlyDropdownFilter),
                   ('created_at', DateTimeRangeFilter)]

    fieldsets = (
        (_('Shop Details'), {
            'fields': ('seller_shop',)}),

        (_('Order Details'), {
            'fields': ('order', 'order_no', 'invoice_no', 'order_status', 'buyer')}),

        (_('Payment Details'), {
            'fields': ('sub_total', 'offer_discount', 'reward_discount', 'order_amount', 'payment_type',
                       'transaction_id')}),
    )

    def seller_shop(self, obj):
        return obj.order.seller_shop

    def buyer(self, obj):
        return obj.order.buyer

    def sub_total(self, obj):
        return obj.order.ordered_cart.subtotal

    def offer_discount(self, obj):
        return obj.order.ordered_cart.offer_discount

    def reward_discount(self, obj):
        return obj.order.ordered_cart.redeem_points_value

    def order_amount(self, obj):
        return obj.order.order_amount

    def order_status(self, obj):
        return obj.order.order_status

    def order_no(self, obj):
        return obj.order.order_no

    def payment_type(self, obj):
        if obj.order.rt_payment_retailer_order.exists():
            ret = ''
            for pay_obj in obj.order.rt_payment_retailer_order.all():
                ret += pay_obj.payment_type.type + ' (' + str(pay_obj.amount) + ')' + ' - '
            return ret
        else:
            return '-'

    def transaction_id(self, obj):
        if obj.order.rt_payment_retailer_order.exists():
            ret = ''
            for pay_obj in obj.order.rt_payment_retailer_order.all():
                if pay_obj.transaction_id:
                    ret += pay_obj.transaction_id + ' (' + str(pay_obj.payment_type.type) + ')' + ' - '
            return ret if ret else '-'
        else:
            return '-'

    def get_queryset(self, request):
        qs = super(RetailerOrderProductAdmin, self).get_queryset(request)
        qs = qs.filter(order__ordered_cart__cart_type='BASIC')
        if request.user.is_superuser:
            return qs
        return qs.filter(order__seller_shop__pos_shop__user=request.user,
                         order__seller_shop__pos_shop__status=True)

    def download_invoice(self, obj):
        if obj.invoice.invoice_pdf:
            return format_html("<a href= '%s' >Download Invoice</a>" % (reverse('admin:pos_download_order_invoice', args=[obj.pk])))
        #invoice_pdf_to_response(263980)
        else:
            return '-'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(RetailerOrderProductAdmin, self).get_urls()
        urls = [
                   url(
                       r'^retailer-order-report/$',
                       self.admin_site.admin_view(RetailerOrderedReportView.as_view()),
                       name="retailer-order-report"
                   ),
                   url(
                       r'^retailer-order-report-form/$',
                       self.admin_site.admin_view(RetailerOrderedReportFormView.as_view()),
                       name="retailer-order-report-form"
                   ),
                    url(
                       r'^retailer-return-report/$',
                       self.admin_site.admin_view(RetailerReturnReportView.as_view()),
                       name="retailer-return-report"
                   ),
                   
                   url(
                       r'^retailer-return-report-form/$',
                       self.admin_site.admin_view(RetailerReturnReportFormView.as_view()),
                       name="retailer-return-report-form"
                   ),
                   url(
                       r'^retailer-order-invoice/(?P<pk>\d+)/$',
                       self.admin_site.admin_view(RetailerOrderProductInvoiceView.as_view()),
                       name="pos_download_order_invoice"
                   )
               ] + urls
        return urls

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass

    def order_data_excel_action(self, request, queryset):
        return create_order_data_excel(queryset, request)

    order_data_excel_action.short_description = "Download CSV of selected orders"


@admin.register(InventoryStatePos)
class PosInventoryStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'inventory_state',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InventoryPos)
class PosInventoryAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'quantity', 'inventory_state', 'created_at', 'modified_at')
    search_fields = ('product__sku', 'product__name', 'product__shop__id', 'product__shop__shop_name',
                     'inventory_state__inventory_state')
    list_per_page = 50
    list_filter = [ProductInvEanSearch]

    @staticmethod
    def shop(obj):
        return obj.product.shop

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super(PosInventoryAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__shop__pos_shop__user=request.user,
                         product__shop__pos_shop__status=True)


    def get_urls(self):
        urls = super(PosInventoryAdmin, self).get_urls()
        urls = [

                   url(r'update_inventory',
                       self.admin_site.admin_view(update_retailer_product_stock),
                       name="update_inventory"),

                   url(r'download_current_inventory',
                       self.admin_site.admin_view(RetailerProductStockDownload),
                       name="download_current_inventory"),

               ] + urls
        return urls

    change_list_template = 'admin/pos/pos_inventory_change_list.html'


@admin.register(InventoryChangePos)
class PosInventoryChangeAdmin(admin.ModelAdmin):
    forms = PosInventoryChangeCSVDownloadForm
    list_display = ('shop', 'product',"Download_PosInventory_Changes", 'quantity', 'transaction_type', 'transaction_id', 'initial_state', 'final_state',
                    'initial_qty', 'final_qty', 'changed_by', 'created_at', 'remarks')
    search_fields = ('product__sku', 'product__name', 'product__shop__id', 'product__shop__shop_name',
                     'transaction_type', 'transaction_id')
    actions = ["posinventorychange_data_excel_action"]
    list_per_page = 50
    list_filter = [ProductInvEanSearch,
                   'transaction_type', ('product__shop', RelatedOnlyDropdownFilter), ('created_at', DateRangeFilter)]

    change_list_template = 'admin/pos/posinventorychange_product_change_list.html'

    def get_queryset(self, request):
        qs = super(PosInventoryChangeAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__shop__pos_shop__user=request.user,
                         product__shop__pos_shop__status=True)

    @staticmethod
    def shop(obj):
        return obj.product.shop

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def Download_PosInventory_Changes(self,obj=None):
        if obj.product.sku_type !=4:
            return format_html("<a href= '%s' >posinventorychange_products_downloads</a>" % (reverse('admin:posinventorychange_products_downloads', args=[obj.product.id])))

        return '-'

    def get_urls(self):
        """" Download CSV of Pos Inventory change along with discounted product"""
        urls = super(PosInventoryChangeAdmin, self).get_urls()
        urls = [
                   url(r'posinventorychange_products_download_form',
                       self.admin_site.admin_view(download_posinventorychange_products_form_view),
                       name="posinventorychange_products_download_form"),

                   url(r'posinventorychange_products_download',
                       self.admin_site.admin_view(download_posinventorychange_products),
                       name="posinventorychange_products_download"),

                    url(
                       r'^retailer-order-invoice/(?P<sku>\d+)/$',
                       self.admin_site.admin_view(download_posinventorychange_products),
                       name="posinventorychange_products_downloads"                   )

               ] + urls
        return urls
    def posinventorychange_data_excel_action(self, request, queryset):

        return posinventorychange_data_excel(request, queryset)

    posinventorychange_data_excel_action.short_description = "Download CSV of selected posinventorychange"


    class Media:
        pass

class RetailerReturnItemsAdmin(admin.TabularInline):
    model = RetailerReturnItems
    fields = ('retailer_product', 'return_qty', 'price', 'return_value')
    readonly_fields = ('retailer_product', 'price', 'return_value')

    @staticmethod
    def price(obj):
        return str(obj.ordered_product.selling_price)

    @staticmethod
    def retailer_product(obj):
        return str(obj.ordered_product.retailer_product)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RetailerOrderReturn)
class RetailerOrderReturnAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ['export_order_return_as_csv']
    list_display = (
    'order_no', 'cart_type', 'download_credit_note', 'status', 'processed_by', 'return_value', 'refunded_amount', 'discount_adjusted', 'refund_points',
    'refund_mode', 'created_at')
    fields = list_display
    list_per_page = 10
    search_fields = ('order__order_no', 'order__buyer__phone_number')
    inlines = [RetailerReturnItemsAdmin]

    def get_queryset(self, request):
        qs = super(RetailerOrderReturnAdmin, self).get_queryset(request)
        qs = qs.filter(order__ordered_cart__cart_type__in=['BASIC', 'ECOM'])
        if request.user.is_superuser:
            return qs
        return qs.filter(order__seller_shop__pos_shop__user=request.user,
                         order__seller_shop__pos_shop__status=True)

    @staticmethod
    def refunded_amount(obj):
        return obj.refund_amount

    def download_credit_note(self, obj):
        if obj.credit_note_order_return_mapping.last() \
            and obj.credit_note_order_return_mapping.last().credit_note_pdf:
            return format_html("<a href= '%s' >Download Credit Note</a>" % (reverse('admin:pos_download_order_return_credit_note', args=[obj.pk])))
        else:
            return '-'

    def cart_type(self, obj):
        return obj.order.ordered_cart.cart_type

    def get_urls(self):
        from django.conf.urls import url
        urls = super(RetailerOrderReturnAdmin, self).get_urls()
        urls = [
                   url(
                       r'^retailer-order-return-credit-note/(?P<pk>\d+)/$',
                       self.admin_site.admin_view(RetailerOrderReturnCreditNoteView.as_view()),
                       name="pos_download_order_return_credit_note"
                   )
               ] + urls
        return urls

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
class OrderCartMappingAdmin(admin.TabularInline):
    model = Order
    fieldsets = (
        (_('Shop Details'), {
            'fields': ('seller_shop',)}),

        (_('Order Details'), {
            'fields': ( 'order_no', 'order_status', 'buyer')}),
    )


    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(RetailerOrderCancel)
class OrderCancelAdmin(admin.ModelAdmin):
    inlines = (RetailerCartProductMappingAdmin, OrderCartMappingAdmin)
    list_per_page = 50
    fields = ('cart_no', 'cart_status', 'cart_type', 'order_id', 'seller_shop', 'buyer', 'offers', 'redeem_points', 'redeem_factor',
              'created_at')
    list_display = ('cart_no', 'cart_status','order_status', 'order_id', 'seller_shop', 'buyer', 'created_at')
    list_filter = (SellerShopFilter, OrderIDFilter, PosBuyerFilter)
    actions = ['order_data_excel_action',]
    def order_status(self, obj):
        return obj.rt_order_cart_mapping.order_status
    # def order_payment_status(self,obj):
    #     return  obj.rt_order_cart_mapping.order_payment
    def get_queryset(self, request):

        qs = super(OrderCancelAdmin, self).get_queryset(request)
        qs = qs.filter(cart_type__in=['BASIC','ECOM'],id__in=Order.objects.filter(order_status='CANCELLED').values('ordered_cart'))
        if request.user.is_superuser:
            return qs
        return qs.filter(seller_shop__pos_shop__user=request.user,
                         seller_shop__pos_shop__status=True)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass

    def order_data_excel_action(self, request, queryset):
        return create_cancel_order_csv(request, queryset)

    order_data_excel_action.short_description = "Download CSV of selected Cancel Orders"



class DiscountedRetailerProductAdmin(admin.ModelAdmin):
    form = DiscountedRetailerProductsForm
    list_display = ('id', 'shop', 'sku', 'product_ref', 'name', 'mrp', 'selling_price', 'product_ean_code', 'image',
                    'linked_product', 'description', 'status', 'created_at', 'modified_at')
    fields = (
    'shop', 'product_ref', 'product_ean_code', 'mrp', 'selling_price', 'discounted_selling_price', 'discounted_stock')
    readonly_fields = ('sku', 'name', 'description', 'sku_type', 'status', 'created_at', 'modified_at')
    list_per_page = 50
    search_fields = ('name', 'product_ean_code')
    list_filter = [ProductEanSearch, ShopFilter]

    change_list_template = 'admin/pos/discounted_product_change_list.html'

    def get_queryset(self, request):
        qs = super(DiscountedRetailerProductAdmin, self).get_queryset(request)
        qs = qs.filter(sku_type=4)
        if request.user.is_superuser:
            return qs
        return qs.filter(shop__pos_shop__user=request.user,
                         shop__pos_shop__status=True)

    @staticmethod
    def image(obj):
        image = obj.retailer_product_image.last()
        if image:
            return format_html('<a href="{}"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.format(
                image.image.url, (image.image_alt_text or image.image_name), image.image.url))

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        """" Download & Upload(For Creating OR Updating Bulk Products) Retailer Product CSV"""
        urls = super(DiscountedRetailerProductAdmin, self).get_urls()
        urls = [
                   url(r'discounted_products_download_form',
                       self.admin_site.admin_view(download_discounted_products_form_view),
                       name="discounted_products_download_form"),

                   url(r'discounted_products_download',
                       self.admin_site.admin_view(download_discounted_products),
                       name="discounted_products_download"),

               ] + urls
        return urls

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'admin/js/pos_discounted_product.js'
        )

    def save_model(self, request, obj, form, change):
        discounted_stock = form.cleaned_data['discounted_stock']
        discounted_price = form.cleaned_data['discounted_selling_price']
        product_status = 'active' if discounted_stock > 0 else 'deactivated'
        product_ref = obj.product_ref
        inventory_initial_state = PosInventoryState.NEW
        tr_type = PosInventoryChange.STOCK_ADD
        user = get_current_user()
        if not obj.id:
            product = RetailerProductCls.create_retailer_product(obj.shop.id, product_ref.name, product_ref.mrp,
                                                                 discounted_price, product_ref.linked_product_id, 4,
                                                                 product_ref.description, product_ref.product_ean_code,
                                                                 user, 'product', product_ref.product_pack_type,
                                                                 product_ref.measurement_category_id,
                                                                 None, product_status, None, None,
                                                                 None, product_ref)

            RetailerProductCls.copy_images(product, product_ref.retailer_product_image.all())
            product.save()
        else:
            product = RetailerProduct.objects.get(id=obj.id)
            RetailerProductCls.update_price(product.id, discounted_price, product_status, user, 'product', product.sku)
            inventory_initial_state = PosInventoryState.AVAILABLE
            tr_type = PosInventoryChange.STOCK_UPDATE
        # Add Inventory
        PosInventoryCls.stock_inventory(product.id, inventory_initial_state, PosInventoryState.AVAILABLE,
                                        discounted_stock, request.user, product.sku,
                                        tr_type)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'vendor_name', 'contact_person_name', 'phone_number', 'alternate_phone_number',
                    'email', 'address', 'pincode', 'gst_number', 'retailer_shop', 'status')
    fields = list_display
    list_per_page = 10
    search_fields = ('company_name', 'vendor_name', 'phone_number', 'retailer_shop__shop_name', 'pincode')

    def get_queryset(self, request):
        qs = super(VendorAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(retailer_shop__pos_shop__user=request.user,
                         retailer_shop__pos_shop__status=True)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class PosCartProductMappingAdmin(admin.TabularInline):
    model = PosCartProductMapping
    fields = ('product', 'qty', 'pack_size', 'price', 'is_grn_done', 'is_bulk')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PosCart)
class PosCartAdmin(admin.ModelAdmin):
    list_display = (
    'po_no', 'vendor', 'download_purchase_order', 'retailer_shop', 'status', 'raised_by', 'last_modified_by',
    'created_at', 'modified_at')
    fields = list_display
    list_per_page = 10
    list_filter = [('retailer_shop', RelatedOnlyDropdownFilter),
                   ('created_at', DateRangeFilter)]
    inlines = [PosCartProductMappingAdmin]
    search_fields = ('po_no', 'retailer_shop__shop_name')
    actions = ['download_store_po']

    def get_queryset(self, request):
        qs = super(PosCartAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(retailer_shop__pos_shop__user=request.user,
                         retailer_shop__pos_shop__status=True)

    def download_purchase_order(self, obj):
        return format_html(
            "<a href= '%s' >Download PO</a>" % (reverse('admin:pos_download_purchase_order', args=[obj.pk])))

    download_purchase_order.short_description = 'Download Purchase Order'

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.conf.urls import url
        urls = super(PosCartAdmin, self).get_urls()
        urls = [
                   url(r'^download-purchase-order/(?P<pk>\d+)/$',
                       self.admin_site.admin_view(DownloadPurchaseOrder.as_view()),
                       name='pos_download_purchase_order'),
               ] + urls
        return urls

    def download_store_po(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['PO No', 'Status', 'Vendor', 'Store Id', 'Store Name', 'Shop User', 'Raised By',
                         'GF Order No', 'Created At', 'SKU', 'Product Name', 'Parent Product', 'Category',
                         'Sub Category',
                         'Brand', 'Sub Brand', 'Quantity', 'Purchase Price', 'Purchase Value', 'linked_product_sku'])

        for obj in queryset:
            for p in obj.po_products.all():
                parent_id, category, sub_category, brand, sub_brand = get_product_details(p.product)
                purchase_value = p.price * p.qty
                writer.writerow([obj.po_no, obj.status, obj.vendor, obj.retailer_shop.id, obj.retailer_shop.shop_name,
                                 obj.retailer_shop.shop_owner, obj.raised_by, obj.gf_order_no,
                                 obj.created_at, p.product.sku, p.product.name, parent_id, category, sub_category,
                                 brand, sub_brand, p.qty, p.price, purchase_value,
                                 p.product.linked_product.product_sku if p.product.linked_product else ''])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=pos_store_po_' + date.today().isoformat() + '.csv'
        return response


class PosGrnOrderProductMappingAdmin(admin.TabularInline):
    model = PosGRNOrderProductMapping
    fields = ('product', 'received_qty')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PosGRNOrder)
class PosGrnOrderAdmin(admin.ModelAdmin):
    list_display = ('grn_id', 'po_no', 'retailer_shop', 'invoice_no', 'invoice_date', 'invoice_amount', 'added_by',
                    'last_modified_by', 'created_at', 'modified_at')
    fields = list_display
    list_per_page = 10
    inlines = [PosGrnOrderProductMappingAdmin]
    list_filter = [('order__ordered_cart__retailer_shop', RelatedOnlyDropdownFilter), ('created_at', DateRangeFilter)]
    search_fields = ('order__ordered_cart__po_no', 'order__ordered_cart__retailer_shop__shop_name')
    actions = ['download_grns']

    def get_queryset(self, request):
        qs = super(PosGrnOrderAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(order__ordered_cart__retailer_shop__pos_shop__user=request.user,
                         order__ordered_cart__retailer_shop__pos_shop__status=True)

    def po_no(self, obj):
        return obj.order.ordered_cart.po_no

    def retailer_shop(self, obj):
        return obj.order.ordered_cart.retailer_shop

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def download_grns(self, request, queryset):
        return download_grn_cvs(queryset)


@admin.register(PaymentType)
class PaymentTypeAdmin(admin.ModelAdmin):
    list_display = ('type', 'enabled', 'app', 'created_at', 'modified_at')
    fields = ('type', 'enabled', 'app')
    list_per_page = 10
    search_fields = ('type',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('type',)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False


class ProductChangeFieldsAdmin(admin.TabularInline):
    model = ProductChangeFields
    fields = ('column_name', 'old_value', 'new_value')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProductChange)
class ProductChangeAdmin(admin.ModelAdmin):
    list_display = ('product', 'event_type', 'event_id', 'changed_by', 'created_at')
    list_per_page = 20
    search_fields = ('product__name', 'product__sku', 'event_type', 'event_id')
    inlines = [ProductChangeFieldsAdmin]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super(ProductChangeAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(product__shop__pos_shop__user=request.user,
                         product__shop__pos_shop__status=True)


class MeasurementUnitAdmin(admin.TabularInline):
    model = MeasurementUnit
    formset = MeasurementUnitFormSet
    fields = ('unit', 'category', 'conversion', 'default')


class PosReturnItemsAdmin(admin.TabularInline):
    model = PosReturnItems
    fields = ('grn_return_id', 'product', 'return_qty',)
    autocomplete_fields = ('product',)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MeasurementCategory)
class MeasurementCategoryAdmin(admin.ModelAdmin):
    list_display = ('category', 'default_unit')
    inlines = [MeasurementUnitAdmin]

    @staticmethod
    def default_unit(obj):
        return MeasurementUnit.objects.filter(category=obj).last().unit


@admin.register(PosReturnGRNOrder)
class PosReturnGRNOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'pr_number',  'status', 'last_modified_by', 'created_at', 'modified_at')
    fields = ('pr_number',  'status', )
    list_per_page = 10
    inlines = [PosReturnItemsAdmin]
    actions = ['download_prn_report']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def download_prn_report(self, request, queryset):
        return generate_prn_csv_report(queryset)


class BulkRetailerProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'products_csv', 'seller_shop', 'uploaded_by', 'created_at', 'modified_at')

    def get_queryset(self, request):
        qs = super(BulkRetailerProductAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.none()

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
class PaymentReconsileAdmin(admin.ModelAdmin):
    list_display = ('id', 'tranjection_id', 'reconcile_status', 'payment_id', 'amount', 'payment_mode', 'created_at', 'modified_at')
    actions = ['delete']
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


admin.site.register(PaymentReconsile, PaymentReconsileAdmin)
admin.site.register(RetailerProduct, RetailerProductAdmin)
admin.site.register(DiscountedRetailerProduct, DiscountedRetailerProductAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(RetailerProductImage, RetailerProductImageAdmin)
admin.site.register(ShopCustomerMap, ShopCustomerMapAdmin)
admin.site.register(RetailerCouponRuleSet, RetailerCouponRuleSetAdmin)
admin.site.register(RetailerCoupon, RetailerCouponAdmin)
admin.site.register(RetailerRuleSetProductMapping, RetailerRuleSetProductMappingAdmin)
admin.site.register(RetailerCart, RetailerCartAdmin)
admin.site.register(RetailerOrderedProduct, RetailerOrderProductAdmin)
admin.site.register(BulkRetailerProduct, BulkRetailerProductAdmin)
