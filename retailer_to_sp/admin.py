import csv

from admin_auto_filters.filters import AutocompleteFilter
from admin_numeric_filter.admin import (NumericFilterModelAdmin,
                                        RangeNumericFilter,
                                        SingleNumericFilter,
                                        SliderNumericFilter)
from dal import autocomplete
from dal_admin_filters import AutocompleteFilter
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.core.exceptions import ValidationError
from django.contrib.admin import SimpleListFilter, helpers
from django.utils.html import format_html, format_html_join
from django.urls import reverse
from django.db.models import Q
from django.db.models import F, FloatField, Sum

from django.forms.models import BaseInlineFormSet
from django import forms
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django_admin_listfilter_dropdown.filters import (ChoiceDropdownFilter,
                                                      DropdownFilter)
from django_select2.forms import ModelSelect2Widget, Select2MultipleWidget
from django.utils.safestring import mark_safe

from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter

from gram_to_brand.models import GRNOrderProductMapping
from products.admin import ExportCsvMixin
from products.models import Product
from retailer_backend.admin import InputFilter
from retailer_to_sp.views import (
    LoadDispatches, UpdateSpQuantity, commercial_shipment_details,
    load_dispatches, order_invoices, ordered_product_mapping_shipment,
    trip_planning, trip_planning_change, update_delivered_qty,
    update_order_status, update_shipment_status, reshedule_update_shipment,
    RetailerCart, assign_picker, assign_picker_change, assign_picker_data,
    UserWithNameAutocomplete
)
from shops.models import ParentRetailerMapping, Shop
from sp_to_gram.models import (
    OrderedProductMapping as SpMappedOrderedProductMapping,
    OrderedProductReserved, create_credit_note,
)
from sp_to_gram.models import OrderedProductReserved, create_credit_note

from .forms import (
    CartForm, CartProductMappingForm, CommercialForm,
    CustomerCareForm, DispatchForm, OrderedProductForm,
    OrderedProductMappingForm,
    OrderedProductMappingShipmentForm,
    ReturnProductMappingForm, ShipmentForm,
    ShipmentProductMappingForm, TripForm, ShipmentReschedulingForm,
    OrderedProductReschedule, OrderedProductMappingRescheduleForm,
    OrderForm, EditAssignPickerForm, ResponseCommentForm
)
from .models import (Cart, CartProductMapping, Commercial, CustomerCare,
                     Dispatch, DispatchProductMapping, Note, Order,
                     OrderedProduct, OrderedProductMapping, Payment, Return,
                     ReturnProductMapping, Shipment, ShipmentProductMapping,
                     Trip, ShipmentRescheduling, Feedback, PickerDashboard,
                     generate_picklist_id, ResponseComment)
from .resources import OrderResource
from .signals import ReservedOrder
from .utils import (
    GetPcsFromQty, add_cart_user, create_order_from_cart,
    reschedule_shipment_button
)


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


class PhoneNumberFilter(InputFilter):
    parameter_name = 'phone_number'
    title = 'Phone Number'

    def queryset(self, request, queryset):
        if self.value() is not None:
            phone_number = self.value()
            return queryset.filter(
                Q(buyer_shop__shop_owner__phone_number=phone_number)
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

class ComplaintIDSearch(InputFilter):
    parameter_name = 'complaint_id'
    title = 'Complaint ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            complaint_id = self.value()
            if complaint_id is None:
                return
            return queryset.filter(
                Q(complaint_id__icontains=complaint_id)
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


class OrderNumberSearch(InputFilter):
    parameter_name = 'order_no'
    title = 'Order No.(Comma seperated)'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            order_nos = order_no.replace(" ", "").replace("\t","").split(',')
            return queryset.filter(
                Q(order__order_no__in=order_nos)
            )


class OrderNoSearch(InputFilter):
    parameter_name = 'order_no'
    title = 'Order No.(Comma seperated)'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            order_nos = order_no.replace(" ", "").replace("\t","").split(',')
            return queryset.filter(
                Q(order_no__in=order_nos)
            )

class IssueStatusSearch(InputFilter):
    parameter_name = 'issue_status'
    title = 'Order Status'

    def queryset(self, request, queryset):
        if self.value() is not None:
            issue_status = self.value()
            if issue_status is None:
                return
            return queryset.filter(
                Q(issue_status__icontains=issue_status)
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
            raise ValidationError("Please add atleast one product to cart!")


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
    form = CartProductMappingForm
    formset = AtLeastOneFormSet
    fields = ('cart', 'cart_product', 'cart_product_price', 'qty',
              'no_of_pieces', 'product_case_size', 'product_inner_case_size')
    autocomplete_fields = ('cart_product', 'cart_product_price')
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'cart_product':
            pass
        return super(CartProductMappingAdmin, self).\
            formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(CartProductMappingAdmin, self) \
            .get_readonly_fields(request, obj)
        if obj:
            readonly_fields = readonly_fields + (
                'cart_product', 'cart_product_price', 'qty', 'no_of_pieces'
            )
        return readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False


class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    fields = ('seller_shop', 'buyer_shop')
    form = CartForm
    list_display = ('order_id', 'seller_shop','buyer_shop','cart_status')
    #change_form_template = 'admin/sp_to_gram/cart/change_form.html'

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}
        js = ('admin/js/product_no_of_pieces.js', 'admin/js/select2.min.js')

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
            ),
            url(
               r'^get-pcs-from-qty/$',
               self.admin_site.admin_view(GetPcsFromQty.as_view()),
               name="GetPcsFromQty"
            ),
            url(r'^commercial/(?P<pk>\d+)/shipment-details/$',
                self.admin_site.admin_view(commercial_shipment_details),
                name="CommercialShipmentDetails"
                ),
            url(r'^user-with-name-autocomplete/$',
                self.admin_site.admin_view(UserWithNameAutocomplete.as_view()),
                name="user_with_name_autocomplete"
                ),
        ] + urls
        return urls

    def get_readonly_fields(self, request, obj):
        readonly_fields = super(CartAdmin, self).get_readonly_fields(request, obj)
        if obj:
            readonly_fields = readonly_fields + ('seller_shop', 'buyer_shop')
        return readonly_fields

    def save_related(self, request, form, formsets, change):
        super(CartAdmin, self).save_related(request, form, formsets, change)
        add_cart_user(form, request)
        create_order_from_cart(form, formsets, request, Order)

        reserve_order = ReservedOrder(
            form.cleaned_data.get('seller_shop'),
            form.cleaned_data.get('buyer_shop'),
            Cart, CartProductMapping, SpMappedOrderedProductMapping,
            OrderedProductReserved, request.user)
        reserve_order.create()


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        list_display = ['order_no', 'seller_shop', 'buyer_shop', 'pincode', 'total_final_amount',
                        'order_status', 'created_at', 'payment_mode', 'paid_amount',
                        'total_paid_amount', 'shipment_status', 'shipment_status_reason','order_shipment_amount', 'order_shipment_details',
                        'picking_status', 'picker_boy', 'picklist_id',]
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field).replace('<br>', '\n') if field in ['shipment_status','shipment_status_reason','order_shipment_amount',
                                  'picking_status', 'picker_boy', 'picklist_id', 'order_shipment_details'] else getattr(obj, field) for field in list_display])
        return response
    export_as_csv.short_description = "Download CSV of Selected Orders"

class SellerShopFilter(AutocompleteFilter):
    title = 'Seller Shop'
    field_name = 'seller_shop'
    autocomplete_url = 'seller-shop-autocomplete'

class BuyerShopFilter(AutocompleteFilter):
    title = 'Buyer Shop'
    field_name = 'buyer_shop'
    autocomplete_url = 'buyer-shop-autocomplete'


# class PickerBoyFilter(AutocompleteFilter):
#     title = 'Picker Boy'
#     field_name = 'picker_boy'
#     autocomplete_url = 'picker-name-autocomplete'

class PickerBoyFilter(InputFilter):
    title = 'Picker Boy'
    parameter_name = 'picker_boy'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(
                Q(picker_boy__first_name__icontains=value) |
                  Q(picker_boy__phone_number=value)
                )
        return queryset


class OrderDateFilter(InputFilter):
    title = 'Order Date'
    parameter_name = 'picker_boy'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(
                Q(picker_boy__first_name__icontains=value) |
                  Q(picker_boy__phone_number=value)
                )
        return queryset


class PicklistIdFilter(InputFilter):
    title = 'Picklist Id'
    parameter_name = 'picklist_id'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(picklist_id=value)
        return queryset


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

class PincodeSearch(InputFilter):
    title = 'Pincode'
    parameter_name = 'pincode'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(order__shipping_address__pincode=value)
        return queryset


class Pincode(InputFilter):
    title = 'Pincode'
    parameter_name = 'pincode'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(shipping_address__pincode=value)
        return queryset
from django.contrib.admin.views.main import ChangeList


class PickerDashboardAdmin(admin.ModelAdmin):
    change_list_template = 'admin/retailer_to_sp/picker/change_list.html'
    #actions = ["change_picking_status"]
    model = PickerDashboard
    raw_id_fields = ['order', 'shipment']

    form = EditAssignPickerForm
    # list_display = (
    #     'id', 'picklist_id', 'picker_boy', 'order_date', 'download_pick_list'
    #     )
    list_display = (
        'picklist', 'picking_status', 'picker_boy',
        'created_at', 'download_pick_list', 'order_number', 'order_date'
        )
    # fields = ['order', 'picklist_id', 'picker_boy', 'order_date']
    #readonly_fields = ['picklist_id']
    list_filter = ['picking_status', PickerBoyFilter, PicklistIdFilter, OrderNumberSearch,('created_at', DateTimeRangeFilter),]

    class Media:
        pass
        #js = ('admin/js/datetime_filter_collapse.js', )

    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('order', 'shipment', 'picklist_id')
        return self.readonly_fields

    def get_urls(self):
        from django.conf.urls import url
        urls = super(PickerDashboardAdmin, self).get_urls()
        urls = [
            url(
               r'^assign-picker/$',
               self.admin_site.admin_view(assign_picker),
               name="AssignPicker"
            ),
            url(
               r'^assign-picker/(?P<shop_id>\d+)/$',
               self.admin_site.admin_view(assign_picker),
               name="AssignPickerWithShop"
            ),
            url(
               r'^assign-picker/(?P<pk>\d+)/change/$',
               self.admin_site.admin_view(assign_picker_change),
               name="AssignPickerChange"
            ),

        ] + urls
        return urls

    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("retailer_to_sp.change_pickerdashboard"):
            return True
        else:
            return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return False

    # def has_module_permission(self, request):
    #     pass

    def change_picking_status(self, request, queryset):
        # queryset.filter(Q(order__picking_status='picking_in_progress')).update(Q(order__picking_status='picking_complete'))
        queryset.update(picking_status='picking_complete')
    change_picking_status.short_description = "Mark selected orders as picking completed"

    def get_queryset(self, request):
        qs = super(PickerDashboardAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs.order_by('-order__created_at')
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                ).order_by('-order__created_at')

    # def _picklist(self, obj, request):
    #     return obj.picklist(request.user)
    def order_number(self,obj):
        return obj.order.order_no
    order_number.short_description = 'Order No'

    def order_date(self,obj):
        return obj.order.created_at
    order_date.short_description = 'Order Date'


    def picklist(self, obj):
        return mark_safe("<a href='/admin/retailer_to_sp/pickerdashboard/%s/change/'>%s<a/>" % (obj.pk,
                                                                                                   obj.picklist_id)
                         )
        # if user.has_perm("can_change_picker_dashboard"):

        # else:
        #     return self.picklist_id
    picklist.short_description = 'Picklist'

    def download_pick_list(self,obj):
        # if obj.picking_status == "picking_complete":
        #     return ""
        if obj.order.order_status not in ["active", "pending"]:
            if obj.shipment:
                return format_html(
                    "<a href= '%s' >Download Pick List</a>" %
                    (reverse('download_pick_list_picker_sp', args=[obj.order.pk, obj.shipment.pk]))
                )
            else:
                return format_html(
                    "<a href= '/retailer/sp/download-pick-list-picker-sp/%s/0/list/' >Download Pick List</a>" %
                    (obj.order.pk)
                )
    download_pick_list.short_description = 'Download Pick List'


class OrderAdmin(NumericFilterModelAdmin,admin.ModelAdmin,ExportCsvMixin):
    actions = ["export_as_csv"]#, "assign_picker"]
    resource_class = OrderResource
    search_fields = ('order_no', 'seller_shop__shop_name', 'buyer_shop__shop_name','order_status')
    form = OrderForm
    fieldsets = (
        (_('Shop Details'), {
            'fields': ('seller_shop', 'buyer_shop',
                       'billing_address', 'shipping_address')}),
        (_('Order Details'), {
            'fields': ('order_no', 'ordered_cart', 'order_status',
                       'cancellation_reason', 'ordered_by',
                       'last_modified_by')}),
        (_('Amount Details'), {
            'fields': ('total_mrp_amount', 'total_discount_amount',
                       'total_tax_amount', 'total_final_amount')}),
        )
    list_select_related =(
        'seller_shop','buyer_shop', 'ordered_cart'
        )
    list_display = (
                    'order_no', 'download_pick_list', 'seller_shop', 'buyer_shop',
                    'pincode','total_final_amount', 'order_status', 'created_at',
                    'payment_mode', 'invoice_no', 'shipment_date', 'invoice_amount', 'shipment_status',
                    'shipment_status_reason', 'delivery_date', 'cn_amount', 'cash_collected',
                    'picking_status', 'picklist_id', 'picker_boy',#'damaged_amount',
                    )

    readonly_fields = ('payment_mode', 'paid_amount', 'total_paid_amount',
                       'invoice_no', 'shipment_status', 'shipment_status_reason','billing_address',
                       'shipping_address', 'seller_shop', 'buyer_shop',
                       'ordered_cart', 'ordered_by', 'last_modified_by',
                       'total_mrp', 'total_discount_amount',
                       'total_tax_amount', 'total_final_amount', 'total_mrp_amount')
    list_filter = [PhoneNumberFilter,SKUFilter, GFCodeFilter, ProductNameFilter, SellerShopFilter,BuyerShopFilter,OrderNoSearch, OrderInvoiceSearch, ('order_status', ChoiceDropdownFilter),
        ('created_at', DateTimeRangeFilter), Pincode]

    # class Media:
    #     js = ('admin/js/dynamic_input_box.js', )

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
        products = obj.ordered_cart.rt_cart_list.all().values('cart_product__product_name')
        for m in products:
            p.append(m)
        return p

    def total_final_amount(self,obj):
        return obj.total_final_amount

    def total_mrp_amount(self,obj):
        return obj.total_mrp_amount

    change_form_template = 'admin/retailer_to_sp/order/change_form.html'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(OrderAdmin, self).get_urls()
        urls += [
            url(r'^retailer-cart/$',
                self.admin_site.admin_view(RetailerCart.as_view()),
                name="retailer_cart"),
        ]
        return urls

class ShipmentReschedulingAdmin(admin.TabularInline):
    model = ShipmentRescheduling
    form = ShipmentReschedulingForm
    fields = ['rescheduling_reason', 'rescheduling_date']
    max_num = 1

    def has_delete_permission(self, request, obj=None):
        return False

class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    form = OrderedProductMappingRescheduleForm
    fields = ['product', 'gf_code', 'ordered_qty', 'shipped_qty',
              'returned_qty', 'damaged_qty', 'delivered_qty']
    readonly_fields = ['ordered_qty', 'product', 'gf_code', 'shipped_qty',
                       'delivered_qty']
    extra = 0
    max_num = 0

    def has_delete_permission(self, request, obj=None):
        return False


class OrderedProductAdmin(admin.ModelAdmin):
    change_list_template = 'admin/retailer_to_sp/OrderedProduct/change_list.html'
    inlines = [ShipmentReschedulingAdmin, OrderedProductMappingAdmin,]
    list_display = (
        'invoice_no', 'order', 'created_at', 'shipment_address', 'invoice_city',
        'invoice_amount', 'payment_mode', 'shipment_status', 'download_invoice'
    )
    exclude = ('received_by', 'last_modified_by')
    fields = (
        'order', 'invoice_no', 'shipment_status', 'trip',
        'return_reason', 'no_of_crates', 'no_of_packets', 'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check'
    )
    autocomplete_fields = ('order',)
    search_fields = ('invoice_no', 'order__order_no')
    readonly_fields = (
        'order', 'invoice_no', 'trip', 'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks'
    )
    form = OrderedProductReschedule

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
        form_instance = getattr(form, 'instance', None)
        formsets_dict = {formset.__class__.__name__: formset
                         for formset in formsets}
        if ('ShipmentReschedulingFormFormSet' in formsets_dict and
            formsets_dict['ShipmentReschedulingFormFormSet'].has_changed() and
                not form.changed_data):
            # if reschedule option selected but not return reason
            reshedule_update_shipment(
                form_instance,
                formsets_dict['OrderedProductMappingFormFormSet']
            )
        elif ('OrderedProductMappingFormFormSet' in formsets_dict and
              formsets_dict[
                'OrderedProductMappingFormFormSet'].has_changed() and
              form.changed_data):
            # if return reason is selected and return qty is entered
            update_shipment_status(
                form_instance,
                formsets_dict['OrderedProductMappingFormFormSet']
            )
            create_credit_note(form.instance)
        update_order_status(
            close_order_checked=False,
            shipment_id=form_instance.id
        )
        super(OrderedProductAdmin, self).save_related(request, form,
                                                      formsets, change)

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
    list_select_related = (
        'order', 'trip', 'order__seller_shop', 'order__shipping_address',
        'order__shipping_address__city',
    )
    list_display = (
        'invoice', 'order', 'created_at', 'trip', 'shipment_address',
        'seller_shop', 'invoice_city', 'invoice_amount', 'payment_mode',
        'shipment_status', 'download_invoice', 'pincode',
    )
    list_filter = [
        ('created_at', DateTimeRangeFilter), InvoiceSearch, ShipmentOrderIdSearch, ShipmentSellerShopSearch,
        ('shipment_status', ChoiceDropdownFilter), PincodeSearch

    ]
    fields = ['order', 'invoice_no', 'invoice_amount', 'shipment_address', 'invoice_city',
        'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks', 'close_order']
    search_fields = [
        'order__order_no', 'invoice_no', 'order__seller_shop__shop_name',
        'order__buyer_shop__shop_name', 'trip__dispatch_no',
        'trip__vehicle_no', 'trip__delivery_boy__phone_number']
    readonly_fields = ['order', 'invoice_no', 'trip', 'invoice_amount', 'shipment_address', 'invoice_city', 'no_of_crates', 'no_of_packets', 'no_of_sacks']
    list_per_page = 50


    def has_delete_permission(self, request, obj=None):
        return False

    def download_invoice(self, obj):
        if obj.shipment_status == 'SHIPMENT_CREATED':
            return format_html("-")
        return format_html(
            "<a href= '%s' >Download Invoice</a>" %
            (reverse('download_invoice_sp', args=[obj.pk]))
        )
    download_invoice.short_description = 'Download Invoice'

    def pincode(self, obj):
        return  obj.order.shipping_address.pincode

    def seller_shop(self, obj):
        return obj.order.seller_shop.shop_name

    def shipment_address(self, obj):
        address = obj.order.shipping_address
        address_line = address.address_line1
        contact = address.address_contact_number
        shop_name = address.shop_name.shop_name
        return str("%s, %s(%s)") % (shop_name, address_line, contact)

    def invoice_city(self, obj):
        city = obj.order.shipping_address.city
        return str(city)

    def invoice(self,obj):
        return obj.invoice_no if obj.invoice_no else format_html(
            "<a href='/admin/retailer_to_sp/shipment/%s/change/' class='button'>Start QC</a>" %(obj.id))
    invoice.short_description = 'Invoice No'


    def save_related(self, request, form, formsets, change):
        #update_shipment_status(form, formsets)

        ordered_qty, shipment_products_dict = update_order_status(
            close_order_checked=form.cleaned_data.get('close_order'),
            shipment_id=form.instance.id
        )

        no_of_pieces = ordered_qty
        shipped_qty = shipment_products_dict.get('shipped_qty',0)

        #when more shipments needed and status == qc_pass
        close_order = form.cleaned_data.get('close_order')
        if close_order:
            form.instance.order.picker_order.update(picking_status="picking_complete")
        change_value = form.instance.shipment_status == form.instance.READY_TO_SHIP
        if "shipment_status" in form.changed_data and change_value and (not close_order):

            if int(no_of_pieces) > shipped_qty:
                try:
                    pincode = "00" #form.instance.order.shipping_address.pincode
                except:
                    pincode = "00"
                PickerDashboard.objects.create(
                    order=form.instance.order,
                    picking_status="picking_pending",
                    picklist_id= generate_picklist_id(pincode) #get_random_string(12).lower(),#
                    )

        if (form.cleaned_data.get('close_order') and
                (form.instance.shipment_status != form.instance.CLOSED and
                 not form.instance.order.order_closed)):

            update_quantity = UpdateSpQuantity(form, formsets)
            update_quantity.update()

        super(ShipmentAdmin, self).save_related(request, form, formsets, change)


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

class ExportCsvMixin:
    def export_as_csv_trip(self, request, queryset):
        meta = self.model._meta
        list_display = ('created_at', 'dispatch_no', 'total_trip_shipments', 'total_trip_amount_value')
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in list_display])
        return response
    export_as_csv_trip.short_description = "Download CSV of Selected Trips"

class TripAdmin(ExportCsvMixin, admin.ModelAdmin):
    change_list_template = 'admin/retailer_to_sp/trip/change_list.html'
    actions = ["export_as_csv_trip",]
    list_display = (
        'dispathces', 'total_trip_shipments', 'total_trip_amount', 'delivery_boy', 'seller_shop', 'vehicle_no',
        'trip_status', 'starts_at', 'completed_at', 'download_trip_pdf'
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

    def download_trip_pdf(self, obj):
        return format_html("<a href= '%s' >Download Trip PDF</a>"%(reverse('download_trip_pdf', args=[obj.pk])))
    download_trip_pdf.short_description = 'Trip Details'


class ExportCsvMixin:
    def export_as_csv_commercial(self, request, queryset):
        meta = self.model._meta
        list_display = ('dispatch_no', 'trip_amount', 'received_amount',
            'cash_to_be_collected', 'delivery_boy', 'vehicle_no', 'trip_status',
            'starts_at', 'completed_at', 'seller_shop',)
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, 'cash_to_be_collected_value') if field in ['cash_to_be_collected'] else getattr(obj, field) for field in list_display])
        return response
    export_as_csv_commercial.short_description = "Download CSV of Selected Commercial"


class ShipmentInlineAdmin(admin.TabularInline):
    model = Shipment
    form = ShipmentForm
    fields = ['product', 'ordered_qty', 'already_shipped_qty', 'to_be_shipped_qty','shipped_qty']
    readonly_fields = ['product', 'ordered_qty', 'to_be_shipped_qty', 'already_shipped_qty']
    extra = 0
    max_num = 0

    def has_delete_permission(self, request, obj=None):
        return False


class CommercialAdmin(ExportCsvMixin, admin.ModelAdmin):
    #change_list_template = 'admin/retailer_to_sp/trip/change_list.html'
    #inlines = [ShipmentInlineAdmin]
    actions = ["change_trip_status", "export_as_csv_commercial",]
    list_display = (
        'dispatch_no', 'trip_amount', #'received_cash_amount',
        'cash_to_be_collected', 'download_trip_pdf', 'delivery_boy',
        'vehicle_no', 'trip_status', 'starts_at', 'completed_at',
        'seller_shop',)
    list_display_links = ('dispatch_no', )
    list_per_page = 10
    list_max_show_all = 100
    list_select_related = ('delivery_boy', 'seller_shop')
    readonly_fields = ('dispatch_no', 'delivery_boy', 'seller_shop',
                        'total_received_amount', 'vehicle_no', 'starts_at', 'trip_amount', 
                       #'received_cash_amount', 'received_online_amount', 
                       'completed_at', 'e_way_bill_no', 'cash_to_be_collected')
    autocomplete_fields = ('seller_shop',)
    search_fields = [
        'delivery_boy__first_name', 'delivery_boy__last_name',
        'delivery_boy__phone_number', 'vehicle_no', 'dispatch_no',
        'seller_shop__shop_name'
    ]
    fields = ['trip_status', 'trip_amount', 'cash_to_be_collected', 'description', 
                'dispatch_no', 'total_received_amount', 
              #'received_cash_amount', 'received_online_amount', 
              'delivery_boy', 'seller_shop', 'starts_at', 'completed_at', 
              'e_way_bill_no', 'vehicle_no']
    list_filter = ['trip_status', ('created_at', DateTimeRangeFilter),
                   ('starts_at', DateTimeRangeFilter), DeliveryBoySearch,
                   ('completed_at', DateTimeRangeFilter), VehicleNoSearch,
                   DispatchNoSearch]
    form = CommercialForm

    def change_trip_status(self, request, queryset):
        queryset.filter(trip_status='CLOSED').update(trip_status='TRANSFERRED')
    change_trip_status.short_description = "Mark selected Trips as Transferred"

    def cash_to_be_collected(self, obj):
        return obj.cash_to_be_collected()
    cash_to_be_collected.short_description = 'Amount to be Collected'

    def total_received_amount(self, obj):
        return obj.total_received_amount
    total_received_amount.short_description = 'Total Received Amount'

    # def received_cash_amount(self, obj):
    #     return obj.received_cash_amount
    # received_cash_amount.short_description = 'Received Cash Amount'

    # def received_online_amount(self, obj):
    #     return obj.received_online_amount
    # received_online_amount.short_description = 'Received Online Amount'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        js = ('admin/js/datetime_filter_collapse.js',
              'admin/js/sweetalert.min.js',
              'admin/js/commercial_trip_status_change.js')

    def get_queryset(self, request):
        qs = super(CommercialAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs.filter(trip_status__in=['COMPLETED', 'CLOSED',
                                              'TRANSFERRED'])
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user),
            trip_status__in=['COMPLETED', 'CLOSED', 'TRANSFERRED'])

    def download_trip_pdf(self, obj):
        return format_html("<a href= '%s' >Download Trip PDF</a>"%(reverse('download_trip_pdf', args=[obj.pk])))
    download_trip_pdf.short_description = 'Trip Details'


class NoteAdmin(admin.ModelAdmin):
    list_display = ('credit_note_id', 'shipment', 'shop', 'amount')
    fields = ('credit_note_id', 'shop', 'shipment', 'note_type', 'amount',
              'invoice_no', 'status')
    readonly_fields = ('credit_note_id', 'shop', 'shipment', 'note_type',
                       'amount', 'invoice_no', 'status')

    class Media:
        pass


class ExportCsvMixin:
    def export_as_csv_customercare(self, request, queryset):
        meta = self.model._meta
        list_display = ('complaint_id', 'complaint_detail', 'retailer_shop', 'retailer_name', 'seller_shop', 'order_id', 'issue_status', 'select_issue', 'issue_date', 'comment_display', 'comment_date_display')
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field).replace('<br>', '\n') if field in ['comment_display','comment_date_display'] else getattr(obj, field) for field in list_display])
        return response
    export_as_csv_customercare.short_description = "Download CSV of Selected CustomeCare"

class ResponseCommentAdmin(admin.TabularInline):
    model = ResponseComment
    form = ResponseCommentForm
    fields = ('comment', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class AddResponseCommentAdmin(admin.TabularInline):
    model = ResponseComment
    form = ResponseCommentForm
    fields = ('comment', )
    extra = 0

    def has_change_permission(self, request, obj=None):
        return False

    # For Django Version > 2.1 there is a "view permission" that needs to be disabled too (https://docs.djangoproject.com/en/2.2/releases/2.1/#what-s-new-in-django-2-1)
    def has_view_permission(self, request, obj=None):
        return False

class CustomerCareAdmin(ExportCsvMixin, admin.ModelAdmin):
    inlines = [ResponseCommentAdmin, AddResponseCommentAdmin]
    model = CustomerCare
    actions = ["export_as_csv_customercare"]
    form = CustomerCareForm
    fields = (
        'phone_number', 'email_us', 'order_id', 'issue_status',
        'select_issue', 'complaint_detail', 'issue_date', 'seller_shop', 'retailer_shop', 'retailer_name'
    )
    exclude = ('complaint_id',)
    list_display = ('complaint_id', 'retailer_shop', 'retailer_name', 'seller_shop', 'contact_number', 'order_id', 'issue_status', 'select_issue', 'issue_date', 'comment_display','comment_date_display')
    autocomplete_fields = ('order_id',)
    search_fields = ('complaint_id',)
    readonly_fields = ('issue_date', 'seller_shop', 'retailer_shop', 'retailer_name')
    list_filter = [ComplaintIDSearch, OrderIdSearch, IssueStatusSearch, IssueSearch]
    #change_form_template = 'admin/retailer_to_sp/customer_care/change_form.html'

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

class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'shipment', 'delivery_experience', 'overall_product_packaging', 'comment', 'created_at', 'status')
    raw_id_fields = ['user', 'shipment']

# admin.site.register(Return, ReturnAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderedProduct, OrderedProductAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(CustomerCare, CustomerCareAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Dispatch, DispatchAdmin)
admin.site.register(Trip, TripAdmin)
admin.site.register(Commercial, CommercialAdmin)
admin.site.register(Shipment, ShipmentAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(PickerDashboard, PickerDashboardAdmin)
