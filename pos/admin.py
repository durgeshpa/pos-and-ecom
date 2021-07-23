import csv
from django.contrib import admin
from django.conf.urls import url
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html

from marketing.filters import UserFilter, PosBuyerFilter
from coupon.admin import CouponCodeFilter, CouponNameFilter, RuleNameFilter, DateRangeFilter
from retailer_to_sp.admin import OrderIDFilter, SellerShopFilter
from wms.models import PosInventory, PosInventoryChange, PosInventoryState

from .models import RetailerProduct, RetailerProductImage, Payment, ShopCustomerMap
from .views import upload_retailer_products_list, download_retailer_products_list_form_view, \
    DownloadRetailerCatalogue, RetailerCatalogueSampleFile, RetailerProductMultiImageUpload
from .proxy_models import RetailerOrderedProduct, RetailerCoupon, RetailerCouponRuleSet, \
    RetailerRuleSetProductMapping, RetailerOrderedProductMapping, RetailerCart, RetailerCartProductMapping,\
    RetailerOrderReturn, RetailerReturnItems
from retailer_to_sp.models import Order, RoundAmount
from shops.models import Shop
from .filters import ShopFilter, ProductInvEanSearch, ProductEanSearch
from .forms import RetailerProductsForm
from .utils import create_order_data_excel


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

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RetailerProductAdmin(admin.ModelAdmin):
    form = RetailerProductsForm
    list_display = ('id', 'shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code', 'image',
                    'linked_product', 'description', 'sku_type', 'status', 'created_at', 'modified_at')
    fields = ('shop', 'linked_product', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
              'description', 'sku_type', 'status', 'created_at', 'modified_at')
    readonly_fields = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
                       'description', 'sku_type', 'status', 'created_at', 'modified_at')
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

    change_list_template = 'admin/pos/pos_change_list.html'

    def get_urls(self):
        """" Download & Upload(For Creating OR Updating Bulk Products) Retailer Product CSV"""
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

               ] + urls
        return urls

    class Media:
        pass


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment_mode', 'paid_by', 'processed_by', 'created_at')
    list_per_page = 10
    search_fields = ('order__order_no', 'paid_by__phone_number')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ShopCustomerMapAdmin(admin.ModelAdmin):
    list_display = ('shop', 'user')
    list_filter = [UserFilter, ShopFilter]
    list_per_page = 10

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
        return qs.filter(coupon_ruleset__shop__shop_type__shop_type='f')

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
        return qs.filter(shop__shop_type__shop_type='f')

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
        return qs.filter(rule__coupon_ruleset__shop__shop_type__shop_type='f')

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
        return qs.filter(cart_type='BASIC')

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
    list_per_page = 10
    list_display = ('order', 'invoice_no', 'order_amount', 'created_at')
    actions = ["order_data_excel_action"]

    fieldsets = (
        (_('Shop Details'), {
            'fields': ('seller_shop',)}),

        (_('Order Details'), {
            'fields': ('order', 'order_no', 'invoice_no', 'order_status', 'buyer')}),

        (_('Amount Details'), {
            'fields': ('sub_total', 'offer_discount', 'reward_discount', 'order_amount')}),
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

    def get_queryset(self, request):
        qs = super(RetailerOrderProductAdmin, self).get_queryset(request)
        qs = qs.filter(order__ordered_cart__cart_type='BASIC')
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
        )

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass

    def order_data_excel_action(self, request, queryset):
        return create_order_data_excel(
            request, queryset, RetailerOrderedProduct, RetailerOrderedProductMapping,
            Order, RetailerOrderReturn,
            RoundAmount, RetailerReturnItems, Shop)
    order_data_excel_action.short_description = "Download CSV of selected orders"

    

@admin.register(PosInventoryState)
class PosInventoryStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'inventory_state',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PosInventory)
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


@admin.register(PosInventoryChange)
class PosInventoryChangeAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'quantity', 'transaction_type', 'transaction_id', 'initial_state', 'final_state',
                    'changed_by', 'created_at')
    search_fields = ('product__sku', 'product__name', 'product__shop__id', 'product__shop__shop_name',
                     'transaction_type', 'transaction_id')
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
class RetailerOrderReturnAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'status', 'processed_by', 'return_value', 'refunded_amount', 'discount_adjusted', 'refund_points',
                    'refund_mode', 'created_at')
    fields = list_display
    list_per_page = 10
    search_fields = ('order__order_no', 'order__buyer__phone_number')
    inlines = [RetailerReturnItemsAdmin]

    @staticmethod
    def refunded_amount(obj):
        return obj.refund_amount

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(RetailerProduct, RetailerProductAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(RetailerProductImage, RetailerProductImageAdmin)
admin.site.register(ShopCustomerMap, ShopCustomerMapAdmin)
admin.site.register(RetailerCouponRuleSet, RetailerCouponRuleSetAdmin)
admin.site.register(RetailerCoupon, RetailerCouponAdmin)
admin.site.register(RetailerRuleSetProductMapping, RetailerRuleSetProductMappingAdmin)
admin.site.register(RetailerCart, RetailerCartAdmin)
admin.site.register(RetailerOrderedProduct, RetailerOrderProductAdmin)
