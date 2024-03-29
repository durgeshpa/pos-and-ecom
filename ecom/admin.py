from os import read
from django.contrib import admin
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse


from marketing.filters import PosBuyerFilter
from pos.filters import ShopFilter
from retailer_to_sp.admin import OrderIDFilter, SellerShopFilter
from retailer_to_sp.models import Order

from .models import Address, Tag, TagProductMapping, EcomCart, EcomCartProductMapping, EcomOrderedProductMapping, \
    EcomOrderedProduct, ShopUserLocationMappedLog
from ecom.utils import generate_ecom_order_csv_report
from .forms import TagProductForm
from ecom.views import DownloadEcomOrderInvoiceView
from ecom.models import EcomTrip
from django.contrib.admin import SimpleListFilter
from rangefilter.filter import DateRangeFilter
from django_admin_listfilter_dropdown.filters import RelatedOnlyDropdownFilter


class EcomCartProductMappingAdmin(admin.TabularInline):
    model = EcomCartProductMapping
    fields = ('cart', 'retailer_product', 'qty', 'product_type', 'selling_price')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False



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


class Seller_SHOP(SimpleListFilter):
    """custom Filter ....."""
    title = 'SellerShop'
    parameter_name = 'seller_shop'
    template = 'django_admin_listfilter_dropdown/dropdown_filter.html'

    def lookups(self, request, model_admin):
        seller_shop = set([s.seller_shop for s in Order.objects.filter(ordered_cart__cart_type='ECOM')])
        return [(s.id, s.shop_name) for s in seller_shop]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(seller_shop=self.value())
        else:
            return queryset


class EcomOrderProductAdmin(admin.ModelAdmin):
    search_fields = ('order_no', 'rt_order_order_product__invoice__invoice_no')
    list_per_page = 10
    list_display = ('order_no', 'order_status', 'buyer_address', 'invoice_no', 'download_invoice', 'created_at',)

    actions = ['download_order_reports']

    fieldsets = (
        (_('Shop Details'), {
            'fields': ('seller_shop',)}),

        (_('Order Details'), {
            'fields': ('id', 'order_no', 'invoice_no', 'order_status', 'order_cancellation_reason', 'buyer',
                       'buyer_address','latitude', 'longitude' )}),

        (_('Amount Details'), {
            'fields': ('sub_total', 'offer_discount', 'reward_discount', 'order_amount')}),
    )
    list_filter = [Seller_SHOP, ('created_at', DateRangeFilter)]

    def seller_shop(self, obj):
        return obj.seller_shop

    def buyer(self, obj):
        return obj.buyer

    def buyer_address(self, obj):
        return str(obj.ecom_address_order.address) + ' ' + str(obj.ecom_address_order.city) + ' ' + str(
            obj.ecom_address_order.state)

    def sub_total(self, obj):
        return obj.ordered_cart.subtotal

    def offer_discount(self, obj):
        try:
            return obj.ordered_cart.offer_discount
        except:
            return float(0)

    def reward_discount(self, obj):
        return obj.ordered_cart.redeem_points_value

    def order_amount(self, obj):
        return obj.order_amount

    def order_status(self, obj):
        return str(obj.order_status).capitalize()

    def order_cancellation_reason(self,obj):
        return obj.get_cancellation_reason_display()

    def order_no(self, obj):
        return obj.order_no

    def latitude(self, obj):
        """return Ecom order latitude"""
        return obj.latitude

    def longitude(self,obj):
        """return Ecom order longitude"""
        return obj.longitude

    def download_invoice(self, obj):
        try:
            if obj.rt_order_order_product.last().invoice.invoice_pdf:
                return format_html("<a href='%s'>Download Invoice</a>" % (reverse('admin:ecom_download_order_invoice', args=[obj.rt_order_order_product.last().pk])))
            else:
                return '-'
        except:
            return '-'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(EcomOrderProductAdmin, self).get_urls()
        urls = [
                   url(
                       r'^ecom-order-invoice/(?P<pk>\d+)/$',
                       self.admin_site.admin_view(DownloadEcomOrderInvoiceView.as_view()),
                       name="ecom_download_order_invoice"
                   )
               ] + urls
        return urls

    def get_queryset(self, request):
        # qs = super(EcomOrderProductAdmin, self).get_queryset(request)
        # qs = qs.filter(order__ordered_cart__cart_type='ECOM')
        # print('='*50)
        # print(len(qs))
        qs = Order.objects.filter(ordered_cart__cart_type='ECOM')
        # print(len(qs))
        # print('=' * 50)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(seller_shop__pos_shop__user=request.user) |
            Q(seller_shop__pos_shop__user_type__in=['manager', 'cashier', 'store_manager',])
        ).distinct()

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def download_order_reports(self, request, queryset):
        return generate_ecom_order_csv_report(queryset)

    class Media:
        pass


@admin.register(Address)
class EcomAddressAdmin(admin.ModelAdmin):
    list_per_page = 10
    fields = ('user', 'type', 'address', 'contact_name', 'contact_number', 'pincode', 'city', 'state',
              'default', 'created_at', 'modified_at', 'deleted_at')
    list_display = fields
    search_fields = ('user__phone_number', 'user__first_name', 'contact_number', 'contact_name', 'pincode',
                     'city__city_name')

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

    def get_fields(self, request, obj=None, **kwargs):
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


@admin.register(EcomTrip)
class EcommerceTripAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'delivery_person','trip_start_at', 'trip_end_at')

    def order_no(self, obj):
        return obj.shipment.order.order_no

    def delivery_person(self, obj):
        return "%s | %s" %  (obj.shipment.order.delivery_person.first_name,
                             obj.shipment.order.delivery_person.phone_number)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class ShopUserLocationMappedLogAdmin(admin.ModelAdmin):
    fields = ('shop', 'user', 'modified_at', )
    list_display = ('shop', 'user', 'modified_at', )
    list_filter = [ShopFilter, ('modified_at', DateRangeFilter)]
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


admin.site.register(EcomOrderedProduct, EcomOrderProductAdmin)
admin.site.register(EcomCart, EcomCartAdmin)
admin.site.register(ShopUserLocationMappedLog, ShopUserLocationMappedLogAdmin)





