from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from retailer_backend.admin import InputFilter
from products.models import Product
from .models import (
    Cart, CartProductMapping, Order, OrderedProduct,
    OrderedProductMapping, Note, CustomerCare, Payment
)
from .forms import (
    CustomerCareForm, OrderedProductForm,
    OrderedProductMappingForm
)
from .views import ordered_product_mapping
from gram_to_brand.models import GRNOrderProductMapping
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from dal import autocomplete


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


class AtLeastOneFormSet(BaseInlineFormSet):
    def clean(self):
        super(AtLeastOneFormSet, self).clean()
        non_empty_forms = 0
        for form in self:
            if form.cleaned_data:
                non_empty_forms += 1
        if non_empty_forms - len(self.deleted_forms) < 1:
            raise ValidationError("Please add at least one product.")


class RequiredInlineFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        form = super(RequiredInlineFormSet, self)._construct_form(i, **kwargs)
        if i < 1:
            form.empty_permitted = False
        return form


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    autocomplete_fields = ('cart_product',)
    formset = AtLeastOneFormSet

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'cart_product':
            pass
        return super(
            CartProductMappingAdmin, self
        ).formfield_for_foreignkey(db_field, request, **kwargs)


class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('order_id', 'shop', 'cart_status', 'last_modified_by')
    list_display = ('order_id', 'cart_status')
    change_form_template = 'admin/sp_to_gram/cart/change_form.html'


class OrderAdmin(admin.ModelAdmin):
    search_fields = ('order',)
    list_display = ('order_no', 'order_status',)

    def get_queryset(self, request):
        qs = super(OrderAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user)
                )


class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    form = OrderedProductMappingForm
    exclude = ('last_modified_by',)
    readonly_fields = ['ordered_qty']
    extra = 0

    warehouse_user_fieldset = ['product', 'shipped_qty', ]
    delivery_user_fieldset = ['product', 'delivered_qty', 'returned_qty',
                              'damaged_qty', ]
    superuser_user_fieldset = ['product', 'shipped_qty','delivered_qty', 'returned_qty',
                              'damaged_qty', ]

    class Media:
        js = (
            'https://code.jquery.com/jquery-3.2.1.js',
            'https://cdnjs.cloudflare.com/ajax/libs/select2/'
            '4.0.6-rc.0/js/select2.min.js'
        )
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/select2/'
                '4.0.6-rc.0/css/select2.min.css',
            )
            }

    def get_fieldsets(self, request, obj=None, **kwargs):
        if request.user.is_superuser:
            self.fields = self.superuser_user_fieldset
        elif request.user.has_perm('sp_to_gram.warehouse_shipment'):
            self.fields = self.warehouse_user_fieldset
        elif request.user.has_perm('sp_to_gram.delivery_from_gf'):
            self.fields = self.delivery_user_fieldset

        return super(OrderedProductMappingAdmin, self).get_fieldsets(request, obj, **kwargs)


class OrderedProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        from django.conf.urls import url
        urls = super(OrderedProductAdmin, self).get_urls()
        urls = [
            url(r'^ajax/load-ordered-products-mapping/$',
                self.admin_site.admin_view(ordered_product_mapping),
                name='ajax_ordered_product_mapping'),
        ] + urls
        return urls

    inlines = [OrderedProductMappingAdmin]
    form = OrderedProductForm
    list_display = ('invoice_no', 'vehicle_no', 'shipped_by',
                    'received_by', 'download_invoice')
    search_fields = ('invoice_no', 'vehicle_no')


    def download_invoice(self, obj):
        return format_html("<a href= '%s' >Download Invoice</a>" %
                           (reverse('download_invoice', args=[obj.pk]))
                           )
    download_invoice.short_description = 'Download Invoice'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('order', )
        return self.readonly_fields

    def get_queryset(self, request):
        qs = super(OrderedProductAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                )


class NoteAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'ordered_product', 'note_type',
        'amount', 'created_at'
    )


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
    list_filter = [
        NameSearch, OrderIdSearch, OrderStatusSearch, IssueSearch
    ]


class PaymentAdmin(admin.ModelAdmin):
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
    list_filter = (NameSearch, OrderIdSearch, PaymentChoiceSearch)


admin.site.register(Payment, PaymentAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderedProduct, OrderedProductAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(CustomerCare, CustomerCareAdmin)
