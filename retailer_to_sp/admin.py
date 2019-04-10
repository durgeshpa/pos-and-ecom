from dal import autocomplete

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter

from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from retailer_backend.admin import InputFilter
from admin_auto_filters.filters import AutocompleteFilter
from django_admin_listfilter_dropdown.filters import DropdownFilter, ChoiceDropdownFilter
from .models import (
    Cart, CartProductMapping, Order, OrderedProduct,
    OrderedProductMapping, Note, CustomerCare,
    Payment, Return, ReturnProductMapping, Dispatch,
    DispatchProductMapping, Trip, Shipment, ShipmentProductMapping
)
from .forms import (
    CustomerCareForm, ReturnProductMappingForm, TripForm, DispatchForm,
    OrderedProductMappingForm, OrderedProductForm, ShipmentForm,
    OrderedProductMappingShipmentForm, ShipmentProductMappingForm
    )
from retailer_to_sp.views import (
    ordered_product_mapping_shipment, order_invoices, trip_planning,
    load_dispatches, trip_planning_change, update_shipment_status,
    update_order_status, update_delivered_qty, UpdateSpQuantity,
    LoadDispatches
    )
from sp_to_gram.models import create_credit_note

from products.admin import ExportCsvMixin
from .resources import OrderResource
from admin_numeric_filter.admin import NumericFilterModelAdmin, SingleNumericFilter, RangeNumericFilter, \
    SliderNumericFilter
from django.http import HttpResponse
import csv


class InvoiceNumberFilter(AutocompleteFilter):
    title = 'Invoice Number'
    field_name = 'invoice_no'


# class ReturnNumberFilter(AutocompleteFilter):
#     title = 'Return No'
#     field_name = 'return_no'


class ReturnNameSearch(InputFilter):
    parameter_name = 'name'
    title = 'Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            name = self.value()
            if name is None:
                return
            return queryset.filter(
                Q(name__icontains=name)
            )


class OrderFilter(InputFilter):
    parameter_name = 'order_no'
    title = 'Order'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            if order_no is None:
                return
            return queryset.filter(
                Q(invoice_no__order__order_no__icontains=order_no)
            )


class NameSearch(InputFilter):
    parameter_name = 'name'
    title = 'Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            name = self.value()
            if name is None:
                return
            return queryset.filter(
                Q(name__icontains=name)
            )

class NEFTSearch(InputFilter):
    parameter_name = 'neft_reference_number'
    title = 'neft reference number'

    def queryset(self, request, queryset):
        if self.value() is not None:
            neft_reference_number = self.value()
            if neft_reference_number is None:
                return
            return queryset.filter(
                Q(neft_reference_number__icontains=neft_reference_number)
            )

class OrderIdSearch(InputFilter):
    parameter_name = 'order_id'
    title = 'Order Id'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_id = self.value()
            if order_id is None:
                return
            return queryset.filter(
                Q(order_id__order_no__icontains=order_id)
            )

class OrderNoSearch(InputFilter):
    parameter_name = 'order_no'
    title = 'Order No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            if order_no is None:
                return
            return queryset.filter(
                Q(order_no__icontains=order_no)
            )

class OrderStatusSearch(InputFilter):
    parameter_name = 'order_status'
    title = 'Order Status'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_status = self.value()
            if order_status is None:
                return
            return queryset.filter(
                Q(order_status__icontains=order_status)
            )


class IssueSearch(InputFilter):
    parameter_name = 'select_issue'
    title = 'Issue'

    def queryset(self, request, queryset):
        if self.value() is not None:
            select_issue = self.value()
            if select_issue is None:
                return
            return queryset.filter(
                Q(select_issue__icontains=select_issue)
            )


class PaymentChoiceSearch(InputFilter):
    parameter_name = 'payment_choice'
    title = 'Payment Mode'

    def queryset(self, request, queryset):
        if self.value() is not None:
            payment_choice = self.value()
            if payment_choice is None:
                return
            return queryset.filter(
                Q(payment_choice__icontains=payment_choice)
            )

class InvoiceSearch(InputFilter):
    parameter_name = 'invoice_no'
    title = 'Invoice No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            invoice_no = self.value()
            if invoice_no is None:
                return
            return queryset.filter(
                Q(invoice_no__icontains=invoice_no)
            )

class OrderInvoiceSearch(InputFilter):
    parameter_name = 'invoice_no'
    title = 'Invoice No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            invoice_no = self.value()
            if invoice_no is None:
                return
            ordered_products = OrderedProduct.objects.select_related('order').filter(invoice_no__icontains=invoice_no)
            return queryset.filter(
                id__in=[op.order_id for op in ordered_products]
            )

class ShipmentOrderIdSearch(InputFilter):
    parameter_name = 'order_id'
    title = 'Order Id'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_id = self.value()
            if order_id is None:
                return
            return queryset.filter(
                Q(order__order_no__icontains=order_id)
            )

class ShipmentSellerShopSearch(InputFilter):
    parameter_name = 'seller_shop_name'
    title = 'Seller Shop'

    def queryset(self, request, queryset):
        if self.value() is not None:
            seller_shop_name = self.value()
            if seller_shop_name is None:
                return
            return queryset.filter(
                Q(order__seller_shop__shop_name__icontains=seller_shop_name)
            )


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    autocomplete_fields = ('cart_product',)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'cart_product':
            pass
        return super(CartProductMappingAdmin, self).\
            formfield_for_foreignkey(db_field, request, **kwargs)


class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('order_id', 'shop', 'cart_status','last_modified_by')
    list_display = ('order_id', 'seller_shop','buyer_shop','cart_status')
    #change_form_template = 'admin/sp_to_gram/cart/change_form.html'

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}

    def get_urls(self):
        from django.conf.urls import url
        urls = super(CartAdmin, self).get_urls()
        urls = [
            url(
                r'^order-product-mapping-shipment/$',
                self.admin_site.admin_view(ordered_product_mapping_shipment),
                name="OrderProductMappingShipment"
            ),
            url(
                r'^order-invoices/$',
                self.admin_site.admin_view(order_invoices),
                name="OrderInvoices"
            ),
            url(
               r'^trip-planning/$',
               self.admin_site.admin_view(trip_planning),
               name="TripPlanning"
            ),
            url(
               r'^load-dispatches/$',
               self.admin_site.admin_view(LoadDispatches.as_view()),
               name="LoadDispatches"
            ),
            url(
               r'^load-dispatches-view/$',
               self.admin_site.admin_view(load_dispatches),
               name="LoadDispatchesView"
            ),
            url(
               r'^trip-planning/(?P<pk>\d+)/change/$',
               self.admin_site.admin_view(trip_planning_change),
               name="TripPlanningChange"
            )
        ] + urls
        return urls

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        flag = 0
        new_order = ''
        for instance in instances:
            instance.last_modified_by = request.user
            instance.save()

            order, _ = Order.objects.get_or_create(
                ordered_cart=instance.cart, order_no=instance.cart.order_id)
            order.ordered_by = request.user
            order.order_status = 'ordered_to_gram'
            order.last_modified_by = request.user
            order.save()
        formset.save_m2m()


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        list_display = ['order_no', 'seller_shop', 'buyer_shop', 'total_final_amount',
                        'order_status', 'created_at', 'payment_amount', 'payment_mode']
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        return response
    export_as_csv.short_description = "Download CSV of Selected Objects"

class SellerShopFilter(AutocompleteFilter):
    title = 'Seller Shop'
    field_name = 'seller_shop'

class BuyerShopFilter(AutocompleteFilter):
    title = 'Buyer Shop'
    field_name = 'buyer_shop'

class SKUFilter(InputFilter):
    title = 'product sku'
    parameter_name = 'product sku'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(ordered_cart__rt_cart_list__cart_product__product_sku=value)
        return queryset

class GFCodeFilter(InputFilter):
    title = 'product gf code'
    parameter_name = 'product gf code'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(ordered_cart__rt_cart_list__cart_product__product_gf_code=value)
        return queryset

class ProductNameFilter(InputFilter):
    title = 'product name'
    parameter_name = 'product name'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(ordered_cart__rt_cart_list__cart_product__product_name=value)
        return queryset

class OrderAdmin(admin.ModelAdmin,ExportCsvMixin):
    actions = ["export_as_csv"]
    resource_class = OrderResource
    search_fields = ('order_no', 'seller_shop__shop_name', 'buyer_shop__shop_name',
                    'order_status',)
    fields = ('order_no', 'ordered_cart', 'order_status', 'seller_shop',
            'buyer_shop', 'billing_address', 'shipping_address', 'total_mrp',
            'total_discount_amount', 'total_tax_amount', 'total_final_amount',
            'ordered_by', 'received_by', 'last_modified_by')
    list_display = ('order_no', 'seller_shop', 'buyer_shop', 'total_final_amount',
                    'order_status', 'created_at', 'payment_mode', 'paid_amount',
                    'total_paid_amount', 'download_pick_list', 'invoice_no',
                    'shipment_status', 'order_shipment_amount')
    readonly_fields = ('payment_mode', 'paid_amount', 'total_paid_amount',
                        'invoice_no', 'order_shipment_amount', 'shipment_status')
    list_filter = [ProductNameFilter,GFCodeFilter,SKUFilter,SellerShopFilter,BuyerShopFilter,OrderNoSearch, OrderInvoiceSearch, ('order_status', ChoiceDropdownFilter),
        ('created_at', DateTimeRangeFilter)]

    class Media:
        pass

    def get_queryset(self, request):
        qs = super(OrderAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user)
                )

    def download_pick_list(self,obj):
        if obj.order_status not in ["active", "pending"]:
            return format_html(
                "<a href= '%s' >Download Pick List</a>" %
                (reverse('download_pick_list_sp', args=[obj.pk]))
            )
    download_pick_list.short_description = 'Download Pick List'

    def order_products(self, obj):
        p=[]
        products = obj.ordered_cart.rt_cart_list.all()
        for m in products:
            p.append(m.cart_product.product_name)
        return p


class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    fields = ['product', 'gf_code', 'ordered_qty', 'shipped_qty', 'returned_qty', 'damaged_qty' , 'delivered_qty']
    readonly_fields = ['ordered_qty', 'product', 'gf_code', 'shipped_qty', 'delivered_qty']
    extra = 0


class OrderedProductAdmin(admin.ModelAdmin):
    change_list_template = 'admin/retailer_to_sp/OrderedProduct/change_list.html'
    inlines = [OrderedProductMappingAdmin]
    list_display = (
        'invoice_no', 'order', 'created_at', 'shipment_address', 'invoice_city',
        'invoice_amount', 'payment_mode', 'shipment_status', 'download_invoice'
    )
    exclude = ('received_by', 'last_modified_by')
    autocomplete_fields = ('order',)
    search_fields = ('invoice_no', 'order__order_no')
    readonly_fields = ('order', 'invoice_no', 'trip', 'shipment_status')

    def download_invoice(self, obj):
        if obj.shipment_status == 'SHIPMENT_CREATED':
            return format_html("-")
        return format_html(
            "<a href= '%s' >Download Invoice</a>" %
            (reverse('download_invoice_sp', args=[obj.pk]))
        )
    download_invoice.short_description = 'Download Invoice'

    def get_queryset(self, request):
        qs = super(OrderedProductAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                )

    def save_related(self, request, form, formsets, change):
        super(OrderedProductAdmin, self).save_related(request, form, formsets, change)
        update_shipment_status(form, formsets)
        update_order_status(form)
        create_credit_note(form)

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}


class DispatchProductMappingAdmin(admin.TabularInline):
    model = DispatchProductMapping
    fields = (
        'product', 'gf_code', 'ordered_qty_no_of_pieces',
        'shipped_qty_no_of_pieces'
    )
    readonly_fields = (
        'product', 'gf_code', 'ordered_qty_no_of_pieces',
        'shipped_qty_no_of_pieces'
    )
    extra = 0
    max_num = 0

    def ordered_qty_no_of_pieces(self, obj):
        return obj.ordered_qty
    ordered_qty_no_of_pieces.short_description = 'Ordered No. of Pieces'

    def shipped_qty_no_of_pieces(self, obj):
        return obj.shipped_qty
    shipped_qty_no_of_pieces.short_description = 'No. of Pieces to Ship'

    def has_delete_permission(self, request, obj=None):
        return False


class DispatchAdmin(admin.ModelAdmin):
    inlines = [DispatchProductMappingAdmin]
    list_display = (
        'invoice_no', 'created_at', 'shipment_address', 'invoice_city',
        'invoice_amount', 'shipment_status', 'trip'
    )
    list_editable = ('shipment_status',)
    list_filter = [
        ('created_at', DateTimeRangeFilter), 'shipment_status',
    ]
    fields = ['order', 'invoice_no', 'invoice_amount','trip', 'shipment_address', 'invoice_city', 'shipment_status']
    readonly_fields = ['order', 'invoice_no', 'trip', 'invoice_amount', 'shipment_address', 'invoice_city']

    def get_queryset(self, request):
        qs = super(DispatchAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}

    def get_queryset(self, request):
        qs = super(DispatchAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                )


class ShipmentProductMappingAdmin(admin.TabularInline):
    model = ShipmentProductMapping
    form = ShipmentProductMappingForm
    fields = ['product', 'ordered_qty', 'already_shipped_qty', 'to_be_shipped_qty','shipped_qty']
    readonly_fields = ['product', 'ordered_qty', 'to_be_shipped_qty', 'already_shipped_qty']
    extra = 0
    max_num = 0

    def has_delete_permission(self, request, obj=None):
        return False


class ShipmentAdmin(admin.ModelAdmin):
    inlines = [ShipmentProductMappingAdmin]
    form = ShipmentForm
    list_display = (
        'invoice_no', 'order', 'created_at', 'shipment_address', 'seller_shop', 'invoice_city',
        'invoice_amount', 'payment_mode', 'shipment_status', 'download_invoice',
    )
    list_filter = [
        ('created_at', DateTimeRangeFilter), InvoiceSearch, ShipmentOrderIdSearch, ShipmentSellerShopSearch,
        ('shipment_status', ChoiceDropdownFilter)

    ]
    search_fields = ['order__order_no', 'invoice_no', 'order__seller_shop__shop_name',
        'order__buyer_shop__shop_name']
    fields = ['order', 'invoice_no', 'invoice_amount', 'shipment_address', 'invoice_city', 'shipment_status']
    readonly_fields = ['order', 'invoice_no', 'trip', 'invoice_amount', 'shipment_address', 'invoice_city']

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}

    def download_invoice(self, obj):
        if obj.shipment_status == 'SHIPMENT_CREATED':
            return format_html("-")
        return format_html(
            "<a href= '%s' >Download Invoice</a>" %
            (reverse('download_invoice_sp', args=[obj.pk]))
        )
    download_invoice.short_description = 'Download Invoice'

    def seller_shop(self, obj):
        return obj.order.seller_shop.shop_name

    def save_related(self, request, form, formsets, change):
        super(ShipmentAdmin, self).save_related(request, form, formsets, change)
        #update_shipment_status(form, formsets)
        update_order_status(form)

    def get_queryset(self, request):
        qs = super(ShipmentAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                )


class DeliveryBoySearch(InputFilter):
    parameter_name = 'delivery_boy'
    title = 'delivery boy'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(delivery_boy__first_name__icontains=self.value()) |
                Q(delivery_boy__phone_number__startswith=self.value()) |
                Q(delivery_boy__last_name__icontains=self.value())
            )


class VehicleNoSearch(InputFilter):
    parameter_name = 'vehicle_no'
    title = 'vehicle no'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(vehicle_no__icontains=self.value())
            )


class DispatchNoSearch(InputFilter):
    parameter_name = 'dispatch_no'
    title = 'dispatch no'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(dispatch_no__icontains=self.value())
            )


class TripAdmin(admin.ModelAdmin):
    change_list_template = 'admin/retailer_to_sp/trip/change_list.html'
    list_display = (
        'dispathces', 'delivery_boy', 'seller_shop', 'vehicle_no',
        'trip_status', 'starts_at', 'completed_at'
    )
    readonly_fields = ('dispathces',)
    autocomplete_fields = ('seller_shop',)

    search_fields = [
        'delivery_boy__first_name', 'delivery_boy__last_name', 'delivery_boy__phone_number',
        'vehicle_no', 'dispatch_no', 'seller_shop__shop_name'
    ]

    list_filter = [
        'trip_status', ('created_at', DateTimeRangeFilter), ('starts_at', DateTimeRangeFilter),
        ('completed_at', DateTimeRangeFilter), DeliveryBoySearch, VehicleNoSearch, DispatchNoSearch
    ]

    class Media:
        js = ('admin/js/datetime_filter_collapse.js', )

    def get_queryset(self, request):
        qs = super(TripAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user)
                )

class NoteAdmin(admin.ModelAdmin):
    list_display = (
        'credit_note_id', 'shipment',
        'invoice_no',  'amount'
    )
    readonly_fields = ['invoice_no', ]
    exclude = ('credit_note_id', 'last_modified_by',)
    # search_fields = (
    #     'credit_note_id',
    #       'amount'
    # )
    # list_filter = [ReturnNumberFilter, ]

    class Media:
        pass

class CustomerCareAdmin(admin.ModelAdmin):
    model = CustomerCare
    form = CustomerCareForm
    fields = (
        'email_us', 'contact_us', 'order_id', 'order_status',
        'select_issue', 'complaint_detail'
    )
    exclude = ('name',)
    list_display = ('name', 'order_id', 'order_status', 'select_issue')
    autocomplete_fields = ('order_id',)
    search_fields = ('name',)
    list_filter = [NameSearch, OrderIdSearch, OrderStatusSearch, IssueSearch]


class PaymentAdmin(NumericFilterModelAdmin,admin.ModelAdmin):
    model = Payment
    fields = (
        'order_id', 'paid_amount', 'payment_choice',
        'neft_reference_number', 'payment_status','imei_no'
    )
    exclude = ('name',)
    list_display = (
        'name', 'order_id', 'paid_amount',
        'payment_choice', 'neft_reference_number','imei_no','created_at',
    )
    autocomplete_fields = ('order_id',)
    search_fields = ('name',)
    list_filter = (NameSearch, OrderIdSearch, PaymentChoiceSearch,('paid_amount', SliderNumericFilter),NEFTSearch)


class ReturnProductMappingAdmin(admin.TabularInline):
    form = ReturnProductMappingForm
    model = ReturnProductMapping
    exclude = ('last_modified_by',)


class ReturnAdmin(admin.ModelAdmin):
    inlines = [ReturnProductMappingAdmin]
    list_display = ('name', 'invoice_no', 'get_order', 'download_credit_note')
    exclude = ('name', 'received_by', 'last_modified_by')
    search_fields = ('name', 'invoice_no__invoice_no', 'name', 'return_no')
    autocomplete_fields = ('invoice_no',)
    list_filter = (InvoiceNumberFilter, ReturnNameSearch, OrderFilter)

    def get_order(self, obj):
        return obj.invoice_no.order
    get_order.short_description = 'Order'

    class Media:
            pass

    def download_credit_note(self, obj):
        if (
            obj.return_credit_note.count() > 0
            and obj.return_credit_note.filter(status=True)
        ):
            return format_html(
                "<a href= '%s' >Download Credit Note</a>" %
                (reverse('download_credit_note', args=[obj.pk]))
            )

    download_credit_note.short_description = 'Download Credit Note'


# admin.site.register(Return, ReturnAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderedProduct, OrderedProductAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(CustomerCare, CustomerCareAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Dispatch, DispatchAdmin)
admin.site.register(Trip, TripAdmin)
admin.site.register(Shipment, ShipmentAdmin)
