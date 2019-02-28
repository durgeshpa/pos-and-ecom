from dal import autocomplete

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget

from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from retailer_backend.admin import InputFilter
from admin_auto_filters.filters import AutocompleteFilter
from .models import (
    Cart, CartProductMapping, Order, OrderedProduct,
    OrderedProductMapping, Note, CustomerCare,
    Payment, Return, ReturnProductMapping
)
from .forms import CustomerCareForm, ReturnProductMappingForm
from retailer_to_sp.views import (
    ordered_product_mapping_shipment, ordered_product_mapping_delivery
)
from sp_to_gram.models import create_credit_note

from products.admin import ExportCsvMixin
from .resources import OrderResource
from admin_numeric_filter.admin import NumericFilterModelAdmin, SingleNumericFilter, RangeNumericFilter, \
    SliderNumericFilter



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


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    autocomplete_fields = ('cart_product',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'cart_product':
            pass
        return super(CartProductMappingAdmin, self).\
            formfield_for_foreignkey(db_field, request, **kwargs)


class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('order_id', 'shop', 'cart_status','last_modified_by')
    list_display = ('order_id', 'cart_status')
    change_form_template = 'admin/sp_to_gram/cart/change_form.html'

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
                r'^order-product-mapping-delivery/$',
                self.admin_site.admin_view(ordered_product_mapping_delivery),
                name="OrderProductMappingDelivery"
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


class OrderAdmin(admin.ModelAdmin,ExportCsvMixin):
    actions = ["export_as_csv"]
    resource_class = OrderResource
    search_fields = ('order_no', 'seller_shop__shop_name', 'buyer_shop__shop_name',
                    'order_status', 'payment_mode')
    list_display = ('order_no', 'seller_shop', 'buyer_shop', 'total_final_amount',
                    'order_status', 'created_at', 'payment_amount', 'payment_mode', 'download_pick_list')


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


class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    exclude = ('last_modified_by',)
    readonly_fields = ('ordered_qty','shipped_qty')
    extra = 0


class OrderedProductAdmin(admin.ModelAdmin):
    change_list_template = 'admin/retailer_to_sp/OrderedProduct/change_list.html'
    inlines = [OrderedProductMappingAdmin]
    list_display = (
        'invoice_no', 'vehicle_no', 'shipped_by',
        'received_by', 'download_invoice'
    )
    exclude = ('shipped_by', 'received_by', 'last_modified_by',)
    autocomplete_fields = ('order',)
    search_fields = ('invoice_no', 'vehicle_no')
    readonly_fields = ('order', 'invoice_no', 'vehicle_no', 'driver_name')

    def download_invoice(self, obj):
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
        create_credit_note(form)

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
        'payment_choice', 'neft_reference_number','imei_no'
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
    exclude = ('name', 'shipped_by', 'received_by', 'last_modified_by')
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


admin.site.register(Return, ReturnAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderedProduct, OrderedProductAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(CustomerCare, CustomerCareAdmin)
admin.site.register(Payment, PaymentAdmin)
