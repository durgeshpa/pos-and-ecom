from django.contrib import admin
from django.conf.urls import url
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from pos.models import RetailerProduct, RetailerProductImage, Payment, UserMappedShop
from pos.views import upload_retailer_products_list, download_retailer_products_list_form_view, \
    DownloadRetailerCatalogue, RetailerCatalogueSampleFile, RetailerProductMultiImageUpload
from pos.forms import RetailerProductsForm
from marketing.filters import UserFilter
from coupon.admin import CouponCodeFilter, CouponNameFilter, RuleNameFilter, DateRangeFilter
from .proxy_models import RetailerOrderedProduct, RetailerCoupon, RetailerCouponRuleSet, \
    RetailerRuleSetProductMapping, RetailerOrderedProductMapping, RetailerCart
from retailer_to_sp.admin import CartProductMappingAdmin, OrderIDFilter, \
    SellerShopFilter
from common.constants import FIFTY
from wms.models import PosInventory, PosInventoryChange, PosInventoryState


class RetailerProductImageAdmin(admin.TabularInline):
    model = RetailerProductImage
    fields = ('image', 'image_thumbnail',)
    readonly_fields = ('image', 'image_thumbnail',)


    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RetailerProductAdmin(admin.ModelAdmin):
    form = RetailerProductsForm
    list_display = ('id', 'shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
                    'linked_product', 'description', 'sku_type', 'status', 'created_at', 'modified_at')
    fields = ('shop', 'linked_product', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
              'description', 'sku_type', 'status', 'created_at', 'modified_at')
    readonly_fields = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
                       'description', 'sku_type', 'status', 'created_at', 'modified_at')
    list_per_page = 50
    inlines = [RetailerProductImageAdmin, ]

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


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment_mode', 'paid_by', 'processed_by', 'created_at')
    
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserMappedShopAdmin(admin.ModelAdmin):
    list_display = ('shop', 'user')
    list_filter = [UserFilter]

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

    search_fields = ('rulename',)
    fields = ('rulename',  'discount', 'free_product', 'free_product_qty', 'cart_qualifying_min_sku_value',
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


class RetailerCartAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super(RetailerCartAdmin, self).get_queryset(request)
        return qs.filter(cart_type='BASIC')

    inlines = [CartProductMappingAdmin]
    fields = ('seller_shop', 'buyer', 'offers', 'approval_status', 'cart_status')
    list_display = ('order_id', 'cart_type', 'approval_status', 'seller_shop', 'buyer', 'cart_status', 'created_at',)
    list_filter = (SellerShopFilter, OrderIDFilter)

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
    fields = ['retailer_product', 'selling_price', 'product_type']

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class RetailerOrderProductAdmin(admin.ModelAdmin):
    inlines = (OrderedProductMappingInline, )
    search_fields = ('invoice__invoice_no', 'order__order_no')
    list_per_page = FIFTY
    list_display = (
        'order', 'invoice_no', 'created_at', 'return_reason',
    )

    fieldsets = (
        (_('Shop Details'), {
            'fields': ('seller_shop', 'buyer')}),

        (_('Ordered Details'), {
            'fields': ('order', 'order_id', 'ordered_cart_id', 'order_status', 'invoice_no', 'return_reason')}),

        (_('Amount Details'), {
            'fields': ('total_mrp_amount', 'total_discount_amount', 'total_tax_amount', 'total_final_amount')}),
    )

    def seller_shop(self, obj):
        return obj.order.seller_shop

    def buyer(self, obj):
        return obj.order.buyer

    def total_final_amount(self, obj):
        return obj.order.total_final_amount

    def total_mrp_amount(self, obj):
        return obj.order.total_mrp_amount

    def total_tax_amount(self, obj):
        return obj.order.total_tax_amount

    def total_discount_amount(self, obj):
        return obj.order.total_discount_amount

    def order_status(self, obj):
        return obj.order.order_status

    def order_id(self, obj):
        return obj.order.id

    def ordered_cart_id(self, obj):
        return obj.order.ordered_cart

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


@admin.register(PosInventoryState)
class PosInventoryStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'inventory_state', )

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PosInventory)
class PosInventoryAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'quantity', 'inventory_state', 'created_at', 'modified_at')
    search_fields = ('product__sku', 'product__name', 'product__shop__id', 'product__shop__shop_name',
                     'inventory_state__inventory_state')

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

    @staticmethod
    def shop(obj):
        return obj.product.shop

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(RetailerProduct, RetailerProductAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(RetailerProductImage)
admin.site.register(UserMappedShop, UserMappedShopAdmin)
admin.site.register(RetailerCouponRuleSet, RetailerCouponRuleSetAdmin)
admin.site.register(RetailerCoupon, RetailerCouponAdmin)
admin.site.register(RetailerRuleSetProductMapping, RetailerRuleSetProductMappingAdmin)
admin.site.register(RetailerCart, RetailerCartAdmin)
admin.site.register(RetailerOrderedProduct, RetailerOrderProductAdmin)