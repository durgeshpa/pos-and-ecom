from django.contrib import admin
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from marketing.filters import PosBuyerFilter
from retailer_to_sp.admin import OrderIDFilter, SellerShopFilter

from .proxy_models import EcomCart, EcomCartProductMapping, EcomOrderedProductMapping, EcomOrderedProduct
from .models import Address, Tag, TagProductMapping
from .forms import TagProductForm


class EcomCartProductMappingAdmin(admin.TabularInline):
    model = EcomCartProductMapping
    fields = ('cart', 'retailer_product', 'qty', 'product_type', 'selling_price')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EcomCart)
class EcomCartAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super(EcomCartAdmin, self).get_queryset(request)
        return qs.filter(cart_type='ECOM')

    list_per_page = 10
    inlines = [EcomCartProductMappingAdmin]
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
    model = EcomOrderedProductMapping
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


@admin.register(EcomOrderedProduct)
class EcomOrderProductAdmin(admin.ModelAdmin):
    inlines = (OrderedProductMappingInline,)
    search_fields = ('invoice__invoice_no', 'order__order_no')
    list_per_page = 10
    list_display = ('order', 'invoice_no', 'created_at')

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
        qs = super(EcomOrderProductAdmin, self).get_queryset(request)
        qs = qs.filter(order__ordered_cart__cart_type='ECOM')
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


@admin.register(Address)
class EcomAddressAdmin(admin.ModelAdmin):
    list_per_page = 10
    fields = ('user', 'type', 'address', 'contact_name', 'contact_number', 'pincode', 'city', 'state',
              'default', 'created_at', 'modified_at', 'deleted_at')
    list_display = fields
    search_fields = ('user__phone_number', 'user__first_name', 'contact_number', 'contact_name', 'pincode',
                     'city')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass

@admin.register(TagProductMapping)
class TagProductMappingAdmin(admin.ModelAdmin):
    form = TagProductForm
    model = TagProductMapping
    list_display = ('tag', 'product', 'shops', 'created_at', 'modified_at')

    def shops(self, obj):
        return obj.product.shop

    def has_delete_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return True
    
    def get_fields (self, request, obj=None, **kwargs):
        fields = super().get_fields(request, obj, **kwargs)
        fields.remove('product')
        fields.append('product')
        return fields

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    model = Tag

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('key',)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return True