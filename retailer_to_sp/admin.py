# python imports
import csv
import logging
import datetime
from operator import or_
from functools import reduce
from dateutil.relativedelta import relativedelta

# django imports
from admin_numeric_filter.admin import (NumericFilterModelAdmin, SliderNumericFilter)
from dal_admin_filters import AutocompleteFilter
from django.contrib import messages, admin
from django.core.exceptions import ValidationError, FieldError
from django.db.models import Q, Count, FloatField, Avg
from django.db.models import F, Sum, OuterRef, Subquery, IntegerField, CharField, Value
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django_admin_listfilter_dropdown.filters import (ChoiceDropdownFilter, RelatedDropdownFilter)
from django.utils.safestring import mark_safe
from django.shortcuts import redirect

from global_config.models import GlobalConfig

# app imports
from rangefilter.filter import DateTimeRangeFilter
from retailer_backend.admin import InputFilter
from retailer_backend.utils import time_diff_days_hours_mins_secs, date_diff_in_seconds
from retailer_to_sp.api.v1.views import DownloadInvoiceSP
from retailer_to_sp.views import (LoadDispatches, commercial_shipment_details, load_dispatches, order_invoices,
                                  ordered_product_mapping_shipment, trip_planning, trip_planning_change,
                                  update_shipment_status_verified, reshedule_update_shipment, RetailerCart, assign_picker,
                                  assign_picker_change, UserWithNameAutocomplete, SellerAutocomplete,
                                  ShipmentOrdersAutocomplete, BuyerShopAutocomplete, BuyerParentShopAutocomplete,
                                  DownloadPickList, DownloadPickListPicker)
from sp_to_gram.models import (
    OrderedProductMapping as SpMappedOrderedProductMapping,
)
from sp_to_gram.models import OrderedProductReserved
from common.constants import DOWNLOAD_BULK_INVOICE, ZERO, FIFTY
from wms.models import Pickup
from .forms import (CartForm, CartProductMappingForm, CommercialForm, CustomerCareForm,
                    ReturnProductMappingForm, ShipmentForm, ShipmentProductMappingForm, ShipmentReschedulingForm,
                    OrderedProductReschedule, OrderedProductMappingRescheduleForm, OrderForm, EditAssignPickerForm,
                    ResponseCommentForm, BulkCartForm, OrderedProductBatchForm, OrderedProductBatchingForm)
from .models import (Cart, CartProductMapping, Commercial, CustomerCare, Dispatch, DispatchProductMapping, Note, Order,
                     OrderedProduct, OrderedProductMapping, Payment, ReturnProductMapping, Shipment,
                     ShipmentProductMapping, Trip, ShipmentRescheduling, Feedback, PickerDashboard, Invoice,
                     ResponseComment, BulkOrder, RoundAmount, OrderedProductBatch, DeliveryData, PickerPerformance)
from .resources import OrderResource
from .signals import ReservedOrder
from .utils import (GetPcsFromQty, add_cart_user, create_order_from_cart, create_order_data_excel,
                    create_invoice_data_excel)
from .filters import (InvoiceAdminOrderFilter, InvoiceAdminTripFilter, InvoiceCreatedAt, DeliveryStartsAt,
                      DeliveryCompletedAt, OrderCreatedAt)
from .tasks import update_order_status_picker_reserve_qty
from payments.models import OrderPayment, ShipmentPayment
from nested_admin import NestedModelAdmin, NestedStackedInline, NestedTabularInline
from retailer_backend.messages import ERROR_MESSAGES

logger = logging.getLogger('django')

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
    parameter_name = 'type_no'
    title = 'Order / Repackaging No.(Comma separated)'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            order_nos = order_no.replace(" ", "").replace("\t","").split(',')
            return queryset.filter(
                Q(order__order_no__in=order_nos) | Q(repackaging__repackaging_no__in=order_nos)
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
        if self.value():
            invoice_no = self.value().split(',')
            return queryset.filter(
                Q(invoice__invoice_no__in=invoice_no)
            )
        return queryset

class OrderInvoiceSearch(InputFilter):
    parameter_name = 'invoice_no'
    title = 'Invoice No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            invoice_no = self.value()
            if invoice_no is None:
                return
            queryset = queryset.filter(rt_order_order_product__invoice__invoice_no__icontains=invoice_no)
            return queryset

class ShipmentOrderIdSearch(InputFilter):
    parameter_name = 'order_id'
    title = 'Order Id'

    def queryset(self, request, queryset):
        if self.value():
            order_id = self.value().split(',')
            return queryset.filter(
                Q(order__order_no__in=order_id)
            )
        return queryset


class ShipmentSellerShopSearch(InputFilter):
    parameter_name = 'seller_shop_name'
    title = 'Seller Shop'

    def queryset(self, request, queryset):
        if self.value():
            seller_shop_name = self.value()
            return queryset.filter(
                Q(order__seller_shop__shop_name__icontains=seller_shop_name)
            )
        return queryset

class SellerShopFilter(AutocompleteFilter):
    field_name = 'seller_shop'
    title = 'seller_shop'
    autocomplete_url = 'admin:seller-autocomplete'


class BuyerShopFilter(AutocompleteFilter):
    field_name = 'buyer_shop'
    title = 'buyer_shop'
    autocomplete_url = 'admin:seller-autocomplete'

class OrderIDFilter(InputFilter):
    parameter_name = 'order_id'
    title = 'order_id'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_id = self.value()
            if order_id is None:
                return
            return queryset.filter(
                Q(order_id__icontains=order_id)
            )

class ShipmentSearch(InputFilter):
    parameter_name = 'shipment_id'
    title = 'Shipment'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shipment_id = self.value()
            if shipment_id is None:
                return
            return queryset.filter(
                Q(shipment__invoice_no__icontains=shipment_id)
            )

class CreditNoteSearch(InputFilter):
    parameter_name = 'credit_note_id'
    title = 'Credit Note'

    def queryset(self, request, queryset):
        if self.value() is not None:
            credit_note_id = self.value()
            if credit_note_id is None:
                return
            return queryset.filter(
                Q(credit_note_id__icontains=credit_note_id)
            )

class ShopSearch(InputFilter):
    parameter_name = 'shop_name'
    title = 'Seller Shop'

    def queryset(self, request, queryset):
        if self.value() is not None:
            shop_name = self.value()
            if shop_name is None:
                return
            return queryset.filter(
                Q(shop__shop_name__icontains=shop_name)
            )

class OrderedProductBatchAdmin(NestedTabularInline):
    model = OrderedProductBatch
    form = OrderedProductBatchForm
    fields = ('batch_id', 'ordered_piece', 'expiry_date','pickup_quantity', 'quantity', 'damaged_qty', 'expired_qty')
    readonly_fields = ('batch_id', 'ordered_piece', 'expiry_date')
    extra=0
    classes = ['batch_inline', ]

    def ordered_piece(self, obj=None):
        return '-'

    def has_delete_permission(self, request, obj=None):
        return False

    # def get_readonly_fields(self, request, obj=None):
    #     if obj and obj.ordered_product.shipment_status != 'SHIPMENT_CREATED':
    #         return self.readonly_fields + ('quantity','damaged_qty','expired_qty' )
    #     return self.readonly_fields



    class Media:
        css = {
            'all': ('admin/css/ordered_product_batch.css',)
        }


class OrderedProductBatchingAdmin(NestedTabularInline):
    model = OrderedProductBatch
    form = OrderedProductBatchingForm
    fields = ('batch_id', 'ordered_piece','expiry_date','quantity','returned_qty','returned_damage_qty','delivered_qty')
    readonly_fields = ('batch_id', 'ordered_piece','expiry_date')
    extra=0
    classes = ['return_batch_inline', ]
    def has_delete_permission(self, request, obj=None):
        return False
    def ordered_piece(self, obj=None):
        return '-'
    class Media:
        css = {
            'all': ('admin/css/ordered_product_batch.css',)
        }

class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    form = CartProductMappingForm
    formset = AtLeastOneFormSet
    fields = ('cart', 'cart_product', 'qty', 'no_of_pieces', 'product_case_size', 'product_inner_case_size',
              'item_effective_prices', 'discounted_price')
    autocomplete_fields = ('cart_product', )
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
                'cart_product', 'qty', 'no_of_pieces', 'item_effective_prices', 'discounted_price'
            )
            # if obj.approval_status == True:
            #     readonly_fields = readonly_fields + (
            #         'discounted_price',
            #     )
            # if obj.cart_type != 'DISCOUNTED':
            #     readonly_fields = readonly_fields + (
            #         'discounted_price',
            #     )
        return readonly_fields
    # def get_readonly_fields(self, request, obj=None):
    #     readonly_fields = super(CartProductMappingAdmin, self) \
    #         .get_readonly_fields(request, obj)
    #     if obj:
    #         readonly_fields = readonly_fields + (
    #             'cart_product', 'cart_product_price', 'item_effective_prices'
    #         )
    #     return readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

class ExportCsvMixinCart:
    def export_as_csv_cart(self, request, queryset):
        meta = self.model._meta
        list_display = ('order_id','seller_shop', 'buyer_shop', 'cart_status', 'date', 'time', 'seller_contact_no', 'buyer_contact_no')
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in list_display])
        return response

    export_as_csv_cart.short_description = "Download CSV of Selected Orders"

class ExportCsvMixinCartProduct:
    def export_as_csv_cart_product(self, request, queryset):
        meta = self.model._meta
        if queryset.count() == 1:
            queryset = queryset.last().rt_cart_list.all()
            list_display = ('cart_product', 'cart_product_sku', 'cart_product_price', 'qty', 'no_of_pieces', 'discounted_price', 'item_effective_prices', 'order_number')
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
            writer = csv.writer(response)
            writer.writerow(list_display)
            for obj in queryset:
                row = writer.writerow([getattr(obj, field) for field in list_display])
            return response
        else:
            messages.error(request, "Please select only one Cart at a time.")

    export_as_csv_cart_product.short_description = "Download CSV of Paticular Cart Products"

class CartAdmin(ExportCsvMixinCart, ExportCsvMixinCartProduct, admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    fields = ('seller_shop', 'buyer_shop', 'offers', 'approval_status')
    actions = ["export_as_csv_cart", "export_as_csv_cart_product" ]
    form = CartForm
    list_display = ('order_id', 'cart_type', 'approval_status', 'seller_shop','buyer_shop','cart_status','created_at',)
    #change_form_template = 'admin/sp_to_gram/cart/change_form.html'
    list_filter = (SellerShopFilter, BuyerShopFilter,OrderIDFilter)

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
            url(r'^seller-autocomplete/$',
                self.admin_site.admin_view( SellerAutocomplete.as_view()),
                name='seller-autocomplete'
                ),
            url(r'^buyer-autocomplete/$',
                self.admin_site.admin_view( BuyerShopAutocomplete.as_view()),
                name='buyer-autocomplete'
                ),
            url(r'^buyer-parent-autocomplete/$',
                self.admin_site.admin_view( BuyerParentShopAutocomplete.as_view()),
                name='buyer-parent-autocomplete'
                ),
            url(r'^plan-shipment-orders-autocomplete/$',
                self.admin_site.admin_view(ShipmentOrdersAutocomplete.as_view()),
                name='ShipmentOrdersAutocomplete'
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
        if change == False:
            add_cart_user(form, request)
            create_order_from_cart(form, formsets, request, Order)
            reserve_order = ReservedOrder(
                form.cleaned_data.get('seller_shop'),
                form.cleaned_data.get('buyer_shop'),
                Cart, CartProductMapping, SpMappedOrderedProductMapping,
                OrderedProductReserved, request.user)
            reserve_order.create()

    def get_readonly_fields(self, request, obj = None):
        if obj:
            count_products = obj.rt_cart_list.all().count()
            count_discounted_prices = obj.rt_cart_list.filter(discounted_price__gt = 0).count()
            if count_products != count_discounted_prices:
                return self.readonly_fields+ ('approval_status',)
            if obj.approval_status == True:
                return self.readonly_fields+ ('approval_status',)
            if obj.rt_cart_list.exists():
                if obj.rt_order_cart_mapping.order_status == 'CANCELLED':
                    return self.readonly_fields+ ('approval_status',)
        return self.readonly_fields


class BulkOrderAdmin(admin.ModelAdmin):
    fields = ('seller_shop', 'buyer_shop', 'shipping_address', 'billing_address', 'cart_products_csv', 'order_type')
    form = BulkCartForm
    list_display = ('cart', 'order_type', 'seller_shop', 'buyer_shop', 'shipping_address', 'billing_address', 'created_at')
    list_filter = (SellerShopFilter, BuyerShopFilter)

    class Media:
        js = ('admin/js/bulk_order.js', 'admin/js/select2.min.js')

    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('seller_shop', 'buyer_shop', 'shipping_address', 'billing_address',)
        return self.readonly_fields

    def has_change_permission(self, request, obj=None):
        if obj:
            return False


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        list_display = ['order_no','seller_shop','buyer_shop_id', 'buyer_shop_with_mobile', 'pincode','city', 'total_final_amount',
                        'order_status', 'created_at', 'payment_mode', 'paid_amount',
                        'total_paid_amount', 'invoice_no', 'shipment_status', 'shipment_status_reason','order_shipment_amount',
                        'trip_completed_at',
                        'picking_status', 'picker_boy', 'picklist_id',]
        field_names = [field.name for field in meta.fields if field.name in list_display]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)

        pickers = PickerDashboard.objects.filter(order__in=queryset, shipment__isnull=True)
        if pickers.exists():
            for picker in pickers:
                obj = picker.order
                row_items = [getattr(obj, field) for field  in list_display if field not in ['trip_completed_at', 'shipment_status','shipment_status_reason','order_shipment_amount',
                                      'invoice_no', 'picking_status', 'picker_boy', 'picklist_id'] ]
                shipment = picker.shipment
                if shipment:
                    row_items += [shipment.invoice_no, shipment.get_shipment_status_display(), shipment.return_reason, shipment.invoice_amount,
                    shipment.trip.completed_at if shipment.trip else '--']
                else:
                    row_items += ["-","-","-","-", "-"]
                row_items += [picker.get_picking_status_display(), picker.picker_boy, picker.picklist_id]

                row = writer.writerow(row_items)

        shipments = OrderedProduct.objects.filter(order__in=queryset)
        if shipments.exists():
            for shipment in shipments:
                obj = shipment.order
                row_items = [getattr(obj, field) for field  in list_display if field not in ['shipment_status','shipment_status_reason','order_shipment_amount',
                                      'trip_completed_at','invoice_no','picking_status', 'picker_boy', 'picklist_id'] ]

                row_items += [shipment.invoice_no, shipment.get_shipment_status_display(), shipment.return_reason, shipment.invoice_amount,
                    shipment.trip.completed_at if shipment.trip else '-',
                    shipment.picking_status, shipment.picker_boy, shipment.picklist_id]

                #getattr(shipment, field) for field in list_display_s]
                row = writer.writerow(row_items)

        # for obj in queryset:
        #     row = writer.writerow([getattr(obj, field).replace('<br>', '\n') if field in ['shipment_status','shipment_status_reason','order_shipment_amount',
        #                           'picking_status', 'picker_boy', 'picklist_id'] else getattr(obj, field) for field in list_display])
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


class PickerDashboardAdmin(admin.ModelAdmin):
    change_list_template = 'admin/retailer_to_sp/picker/change_list.html'
    actions = ["download_bulk_pick_list"]
    list_per_page = FIFTY
    model = PickerDashboard
    raw_id_fields = ['order', 'shipment']

    form = EditAssignPickerForm
    # list_display = (
    #     'id', 'picklist_id', 'picker_boy', 'order_date', 'download_pick_list'
    #     )
    list_display = (
        'picklist', 'picking_status', 'picker_boy',
        'created_at', 'picker_assigned_date', 'download_pick_list', 'picklist_status', 'picker_type', 'order_number',
        'order_date', 'refreshed_at', 'picking_completion_time')
    # fields = ['order', 'picklist_id', 'picker_boy', 'order_date']
    #readonly_fields = ['picklist_id']
    list_filter = ['picking_status', PickerBoyFilter, PicklistIdFilter, OrderNumberSearch,('created_at', DateTimeRangeFilter),]

    class Media:
        js = ('admin/js/picker.js', )
        #js = ('admin/js/datetime_filter_collapse.js', )

    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('order', 'shipment', 'picklist_id', 'repackaging')
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
        queryset.update(picking_status='picking_complete', completed_at=datetime.datetime.now())
    change_picking_status.short_description = "Mark selected orders as picking completed"

    def get_queryset(self, request):
        qs = super(PickerDashboardAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs.order_by('-order__created_at')
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user) |
            Q(repackaging__seller_shop__related_users=request.user) |
            Q(repackaging__seller_shop__shop_owner=request.user)
                ).order_by('-order__created_at')

    # def _picklist(self, obj, request):
    #     return obj.picklist(request.user)
    def order_number(self,obj):
        if obj.order:
            return obj.order.order_no
        elif obj.repackaging:
            return obj.repackaging.repackaging_no
    order_number.short_description = 'Order / Repackaging No'

    def picker_type(self,obj):
        if obj.repackaging:
            return 'Repackaging'
        elif obj.order:
            return 'Order'
    picker_type.short_description = 'Type'

    def order_date(self,obj):
        if obj.order:
            return obj.order.created_at
        elif obj.repackaging:
            return obj.repackaging.created_at
    order_date.short_description = 'Order / Repackaging Date'

    def picklist_status(self, obj):
        picklist_status = 'Valid'
        if not obj.is_valid:
            picklist_status = 'Cancelled'
        return picklist_status


    def completed_at(self, obj):
        """
        Returns the time when picking was completed
        return completed_at if completed_at is set in  else fetch the completed_at from Pickup table
        """
        if obj.completed_at:
            return obj.completed_at
        if obj.order:
            if Pickup.objects.filter(pickup_type_id=obj.order.order_no, status='picking_complete').exists():
                return Pickup.objects.filter(pickup_type_id=obj.order.order_no,
                                             status='picking_complete').last().completed_at

    def picking_completion_time(self, obj):
        """
        Returns the duration between picking creation and picking completion
        returned value format  x days n hrs m mins y secs
        """
        completed_at = self.completed_at(obj)
        if completed_at:
            return time_diff_days_hours_mins_secs(completed_at, obj.picker_assigned_date)



    def picklist(self, obj):
        return mark_safe("<a href='/admin/retailer_to_sp/pickerdashboard/%s/change/'>%s<a/>" % (obj.pk,
                                                                                                   obj.picklist_id)
                         )
        # if user.has_perm("can_change_picker_dashboard"):

        # else:
        #     return self.picklist_id
    picklist.short_description = 'Picklist'

    def download_pick_list(self, obj):
        if obj.order:
            if obj.order.order_status not in ["active", "pending"]:
                return format_html(
                    "<a href= '%s' >Download Pick List</a>" %
                    (reverse('create-picklist', args=[obj.order.pk]))
                )
        elif obj.repackaging:
            return format_html(
                "<a href= '%s' >Download Pick List</a>" %
                (reverse('create-picklist', kwargs={'pk': obj.repackaging.pk, 'type': 2}))
            )

    def download_bulk_pick_list(self, request, *args, **kwargs):
        """

        :param request: request params
        :param args: argument list
        :param kwargs: keyword argument
        :return: response
        """
        if len(args[0]) <= FIFTY:
            # argument_list contains list of pk
            kwargs = {}
            argument_list = []
            for arg in args[ZERO]:
                if arg.order:
                    if arg.order.order_status not in ["active", "pending"]:
                        if arg.shipment:
                            # append pk which are not falling under the order active and pending
                            kwargs.update({arg.order.pk: arg.shipment.pk})
                        else:
                            kwargs.update({arg.order.pk: '0'})
                    else:
                        pass
                elif arg.repackaging:
                    kwargs.update({arg.repackaging.pk: 'repackaging'})
            # call get method under the DownloadPickListPicker class
            response = DownloadPickListPicker.get(self, request, argument_list, kwargs)
            if response[1] is True:
                return redirect(response[0])
            else:
                return response[0]
        else:
            response = messages.error(request, ERROR_MESSAGES["4001"])
        return response

    download_pick_list.short_description = 'Download Pick List'
    download_bulk_pick_list.short_description = 'Download Pick List for Selected Orders/Repackagings'


class OrderAdmin(NumericFilterModelAdmin,admin.ModelAdmin,ExportCsvMixin):
    actions = ['order_data_excel_action', "download_bulk_pick_list"]
    resource_class = OrderResource
    search_fields = ('order_no', 'seller_shop__shop_name', 'buyer_shop__shop_name','order_status')
    form = OrderForm
    list_per_page = FIFTY
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
                    'order_no', 'download_pick_list', 'invoice_no', 'seller_shop','buyer_shop_id', 'buyer_shop_type', 'buyer_shop_with_mobile',
                    'pincode', 'city', 'total_final_amount', 'order_status', 'created_at',
                    'payment_mode', 'shipment_date', 'invoice_amount', 'shipment_status', 'trip_id',
                    'shipment_status_reason', 'delivery_date', 'cn_amount', 'cash_collected',
                    'picking_status', 'picklist_id', 'picklist_refreshed_at', 'picker_boy',
                    'pickup_completed_at', 'picking_completion_time' #'damaged_amount',
                    )

    readonly_fields = ('payment_mode', 'paid_amount', 'total_paid_amount',
                       'invoice_no', 'shipment_status', 'shipment_status_reason','billing_address',
                       'shipping_address', 'seller_shop', 'buyer_shop',
                       'ordered_cart', 'ordered_by', 'last_modified_by',
                       'total_mrp', 'total_discount_amount',
                       'total_tax_amount', 'total_final_amount', 'total_mrp_amount')
    list_filter = [PhoneNumberFilter,SKUFilter, GFCodeFilter, ProductNameFilter, SellerShopFilter,BuyerShopFilter,OrderNoSearch, OrderInvoiceSearch, ('order_status', ChoiceDropdownFilter),
        ('created_at', DateTimeRangeFilter), Pincode, ('shipping_address__city', RelatedDropdownFilter)]

    class Media:
        js = ('admin/js/picker.js', )

    def get_queryset(self, request):
        qs = super(OrderAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user)
                )

    def buyer_shop_type(self, obj):
        return obj.buyer_shop.shop_type

    def download_pick_list(self,obj):
        if obj.order_status not in ["active", "pending"]:
            return format_html(
                "<a href= '%s' >Download Pick List</a>" %
                (reverse('create-picklist', args=[obj.pk]))
            )

    def download_bulk_pick_list(self, request, *args, **kwargs):
        """

        :param request: request params
        :param args: argument list
        :param kwargs: keyword argument
        :return: response
        """
        if len(args[0]) <= FIFTY:
            # argument_list contains list of pk
            argument_list = []
            for arg in args[ZERO]:
                if arg.order_status not in ["active", "pending"]:
                    # append pk which are not falling under the order active and pending
                    argument_list.append(arg.pk)
                else:
                    pass
            # call get method under the DownloadPickList class
            response = DownloadPickList.get(self, request, argument_list, **kwargs)
            if response[1] is True:
                return redirect(response[0])
            else:
                return response[0]
        else:
            response = messages.error(request, ERROR_MESSAGES["4001"])
        return response

    download_pick_list.short_description = 'Download Pick List'
    download_bulk_pick_list.short_description = 'Download Pick List for Selected Orders'

    def order_products(self, obj):
        p=[]
        products = obj.ordered_cart.rt_cart_list.all().values('cart_product__product_name')
        for m in products:
            p.append(m)
        return p

    def total_final_amount(self,obj):
        return obj.order_amount

    def total_mrp_amount(self,obj):
        return obj.total_mrp

    def picking_completion_time(self, obj):
        pd_entry = PickerDashboard.objects.filter(order=obj, picking_status='picking_complete').last()
        if pd_entry and pd_entry.completed_at:
            return time_diff_days_hours_mins_secs(pd_entry.completed_at, pd_entry.picker_assigned_date)

        pickup_object = Pickup.objects.filter(pickup_type_id=obj.order_no, status='picking_complete').last()
        if pickup_object is not None and pickup_object.completed_at is not None:
            return time_diff_days_hours_mins_secs(pickup_object.completed_at, pickup_object.created_at)

    change_form_template = 'admin/retailer_to_sp/order/change_form.html'

    def order_data_excel_action(self, request, queryset):
        return create_order_data_excel(
            request, queryset, OrderPayment, ShipmentPayment,
            OrderedProduct, Order, Trip, PickerDashboard,
            RoundAmount)
    order_data_excel_action.short_description = "Download CSV of selected orders"

    def get_urls(self):
        from django.conf.urls import url
        urls = super(OrderAdmin, self).get_urls()
        urls += [
            url(r'^retailer-cart/$',
                self.admin_site.admin_view(RetailerCart.as_view()),
                name="retailer_cart"),
        ]
        return urls


class ShipmentReschedulingAdminNested(NestedTabularInline):
    model = ShipmentRescheduling
    form = ShipmentReschedulingForm
    fields = ['rescheduling_reason', 'rescheduling_date']
    max_num = 1

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ShipmentRescheduling)
class ShipmentReschedulingAdmin(admin.ModelAdmin):
    model = ShipmentRescheduling
    list_display = ('shipment', 'order', 'trip', 'rescheduling_reason', 'rescheduling_date', 'created_by')
    list_per_page = 20
    search_fields = ('shipment__order__order_no', 'shipment__invoice__invoice_no', 'trip__dispatch_no')

    def order(self, obj):
        return obj.shipment.order

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class OrderedProductMappingAdmin(NestedTabularInline):
    model = OrderedProductMapping
    form = OrderedProductMappingRescheduleForm
    fields = ['product', 'ordered_qty','expiry_date','shipped_qty',
              'returned_qty', 'returned_damage_qty', 'delivered_qty']
    readonly_fields = ['ordered_qty','expiry_date','product', 'gf_code',
                       'cancellation_date']
    inlines = [OrderedProductBatchingAdmin, ]
    extra = 0
    max_num = 0
    classes = ['return_table_inline', ]
    def has_delete_permission(self, request, obj=None):
        return False

    def expiry_date(self, obj=None):
        return '-'


class OrderedProductAdmin(NestedModelAdmin):
    change_list_template = 'admin/retailer_to_sp/OrderedProduct/change_list.html'
    actions = ['download_bulk_invoice']
    list_per_page = FIFTY
    inlines = [ShipmentReschedulingAdminNested, OrderedProductMappingAdmin,]
    list_display = (
        'invoice_no', 'order', 'created_at', 'shipment_address', 'invoice_city',
        'invoice_amount', 'payment_mode', 'shipment_status', 'download_invoice'
    )
    exclude = ('received_by', 'last_modified_by')
    fields = (
        'order', 'invoice_no', 'shipment_status', 'trip',
        'return_reason', 'no_of_crates', 'no_of_packets', 'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check',
        'previous_trip'
    )
    autocomplete_fields = ('order',)
    search_fields = ('invoice__invoice_no', 'order__order_no')
    readonly_fields = (
        'order', 'invoice_no', 'trip', 'no_of_crates', 'no_of_packets', 'no_of_sacks', 'previous_trip'
    )
    form = OrderedProductReschedule
    ordering = ['-created_at']
    classes = ['table_inline', ]

    def previous_trip(self, obj):
        if obj and obj.rescheduling_shipment.all().exists():
            return obj.rescheduling_shipment.last().trip
        return '-'

    def download_invoice(self, obj):
        if obj.shipment_status == 'SHIPMENT_CREATED':
            return format_html("-")
        return format_html(
            "<a href= '%s' >Download Invoice</a>" %
            (reverse('download_invoice_sp', args=[obj.pk]))
        )
    download_invoice.short_description = 'Download Invoice'

    def download_bulk_invoice(self, request, *args, **kwargs):
        """

        :param request: request params
        :param args: argument list
        :param kwargs: keyword argument
        :return: response
        """
        response = ShipmentAdmin.download_bulk_invoice(self, request, *args, **kwargs)
        return response

    # download bulk invoice short description
    download_bulk_invoice.short_description = DOWNLOAD_BULK_INVOICE

    def get_queryset(self, request):
        qs = super(OrderedProductAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
        )

    def save_related(self, request, form, formsets, change):
        complete_shipment_status = ['FULLY_RETURNED_AND_COMPLETED','PARTIALLY_DELIVERED_AND_COMPLETED',
                                    'FULLY_DELIVERED_AND_COMPLETED']
        form_instance = getattr(form, 'instance', None)
        formsets_dict = {formset.__class__.__name__: formset
                         for formset in formsets}
        if (not form_instance.rescheduling_shipment.exists()) and ('ShipmentReschedulingFormFormSet' in formsets_dict and
            [i for i in formsets_dict['ShipmentReschedulingFormFormSet'].cleaned_data if i]):
            reshedule_update_shipment(form_instance, formsets_dict['OrderedProductMappingFormFormSet'],
                                      formsets_dict['ShipmentReschedulingFormFormSet'])
        elif form_instance.shipment_status in complete_shipment_status:
            update_shipment_status_verified(form_instance, formsets_dict['OrderedProductMappingFormFormSet'])
            #create_credit_note(form.instance)
        # update_order_status(
        #     close_order_checked=False,
        #     shipment_id=form_instance.id
        # )
        super(OrderedProductAdmin, self).save_related(request, form,
                                                      formsets, change)

    class Media:
        css = {"all": ("admin/css/hide_admin_inline_object_name.css",)}
        js = ('admin/js/shipment.js','https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js')


class DispatchProductMappingAdmin(admin.TabularInline):
    model = DispatchProductMapping
    fields = (
        'product', 'gf_code', 'ordered_qty_no_of_pieces',
        'shipped_qty_no_of_pieces', 'product_weight'
    )
    readonly_fields = (
        'product', 'gf_code', 'ordered_qty_no_of_pieces',
        'shipped_qty_no_of_pieces', 'product_weight'
    )
    extra = 0
    max_num = 0

    def ordered_qty_no_of_pieces(self, obj):
        return obj.ordered_qty
    ordered_qty_no_of_pieces.short_description = 'Ordered No. of Pieces'

    def shipped_qty_no_of_pieces(self, obj):
        return obj.shipped_qty
    shipped_qty_no_of_pieces.short_description = 'No. of Pieces to Ship'

    def product_weight(self, obj):
        return obj.product_weight
    product_weight.short_description = 'Product Weight'


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
    fields = ['order', 'invoice_no', 'invoice_amount','trip', 'shipment_address', 'invoice_city', 'shipment_weight','shipment_status']
    readonly_fields = [
        'order', 'invoice_no', 'trip', 'invoice_amount', 'shipment_address',
        'invoice_city', 'shipment_weight', 'shipment_status']

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

    def shipment_weight(self, obj):
        return obj.shipment_weight
    shipment_weight.short_description = 'Shipment Weight'

    def get_queryset(self, request):
        qs = super(DispatchAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                )


class ShipmentProductMappingAdmin(NestedTabularInline):
    model = ShipmentProductMapping
    form = ShipmentProductMappingForm
    inlines = [OrderedProductBatchAdmin, ]
    fields = ['product', 'ordered_qty','expiry_date','picked_pieces','shipped_qty', 'damaged_qty', 'expired_qty']
    readonly_fields = ['product', 'ordered_qty', 'expiry_date']
    extra = 0
    max_num = 0
    classes = ['table_inline', ]
    def has_delete_permission(self, request, obj=None):
        return False


    def expiry_date(self, obj=None):
        return "-"

    # def get_readonly_fields(self, request, obj=None):
    #     if obj and obj.shipment_status == 'READY_TO_SHIP':
    #         return self.readonly_fields + ['shipped_qty','damaged_qty','expired_qty']
    #     return self.readonly_fields


class ShipmentAdmin(NestedModelAdmin):
    has_invoice_no = True
    inlines = [ShipmentProductMappingAdmin]
    form = ShipmentForm
    actions = ['download_bulk_invoice']
    list_select_related = (
        'order', 'trip', 'order__seller_shop', 'order__shipping_address',
        'order__shipping_address__city',
    )
    list_display = (
        'start_qc', 'order', 'created_at', 'trip', 'shipment_address',
        'seller_shop', 'invoice_city', 'invoice_amount', 'payment_mode',
        'shipment_status', 'download_invoice', 'pincode',
    )
    list_filter = [
        ('created_at', DateTimeRangeFilter), InvoiceSearch, ShipmentOrderIdSearch,
        ShipmentSellerShopSearch, ('shipment_status', ChoiceDropdownFilter), PincodeSearch
    ]
    fields = ['order', 'invoice_no', 'invoice_amount', 'shipment_address', 'invoice_city',
              'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks', 'close_order']
    search_fields = [
        'order__order_no', 'invoice__invoice_no', 'order__seller_shop__shop_name',
        'order__buyer_shop__shop_name', 'trip__dispatch_no',
        'trip__vehicle_no', 'trip__delivery_boy__phone_number']
    readonly_fields = ['order', 'invoice_no', 'trip', 'invoice_amount', 'shipment_address',
                       'invoice_city', 'no_of_crates', 'no_of_packets', 'no_of_sacks']
    list_per_page = FIFTY
    ordering = ['-created_at']

    def get_search_results(self, request, queryset, search_term):
        """
        request:-request object
        queryset:-queryset object
        search_term:- search strings

        """
        queryset, use_distinct = super(ShipmentAdmin, self).get_search_results(
            request, queryset, search_term)
        if queryset:
            return queryset, use_distinct
        else:
            search_words = search_term.split(',')
            if search_words:
                q_objects = [Q(**{field + '__icontains': word})
                             for field in self.search_fields
                             for word in search_words]
                queryset |= self.model.objects.filter(reduce(or_, q_objects))

            return queryset, use_distinct

    def has_delete_permission(self, request, obj=None):
        return False

    def download_invoice(self, obj):
        if obj.shipment_status == 'SHIPMENT_CREATED' or obj.invoice_no == '-':
            return format_html("-")
        return format_html(
            "<a href= '%s' >Download Invoice</a>" %
            (reverse('download_invoice_sp', args=[obj.pk]))
        )

    def download_bulk_invoice(self, request, *args, **kwargs):
        """

        :param request: request parameter
        :param args: argument list
        :param kwargs: keyword argument
        :return: response
        """

        if len(args[0]) <= FIFTY:
            # argument_list contains list of pk exclude shipment created and blank invoice
            argument_list = []
            for arg in args[ZERO]:
                # check condition for QC pending status file
                if arg.shipment_status == OrderedProduct.SHIPMENT_STATUS[ZERO][ZERO] or arg.invoice_no == '-':
                    pass
                else:
                    # append pk which are not falling under the shipment created and blank invoice number
                    argument_list.append(arg.pk)
            # if we are getting only QC pending status files for downloading
            if len(argument_list) == 0:
                response = messages.error(request, ERROR_MESSAGES["4002"])
                return response
            # call get method under the DownloadInvoiceSP class
            try:
                response = DownloadInvoiceSP.get(self, request, argument_list, **kwargs)
                if response[1] is True:
                    return redirect(response[0])
                else:
                    return response[0]
            except Exception as e:
                logger.exception(e)
                return redirect(request.META['HTTP_REFERER'])
        else:
            response = messages.error(request, ERROR_MESSAGES["4001"])
        return response
    # download single invoice short description
    download_bulk_invoice.short_description = 'Download Invoice'
    # download bulk invoice short description
    download_bulk_invoice.short_description = DOWNLOAD_BULK_INVOICE

    class Media:
        js = ('admin/js/shipment.js','https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js')


    def pincode(self, obj):
        return obj.order.shipping_address.pincode

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

    def start_qc(self,obj):
        if obj.order.order_status == Order.CANCELLED:
            return format_html("<a href='/admin/retailer_to_sp/shipment/%s/change/' class='button'>Order Cancelled</a>" %(obj.id))

        return obj.invoice_no if obj.invoice_no != '-' else format_html(
            "<a href='/admin/retailer_to_sp/shipment/%s/change/' class='button'>Start QC</a>" %(obj.id))
    start_qc.short_description = 'Invoice No'

    def save_model(self, request, obj, form, change):
        if not hasattr(form.instance, 'invoice') and (form.cleaned_data.get('shipment_status', None) == form.instance.READY_TO_SHIP):
            self.has_invoice_no = False
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super(ShipmentAdmin, self).save_related(request, form, formsets, change)

        # when qc passed
        if not self.has_invoice_no:
            # delay function to generate pdf from qc pending to qa passed
            # request = jsonpickle.encode(request, unpicklable=False)
            # pdf_generation.delay(request, form.instance.pk)
            shipment_products_dict = form.instance.rt_order_product_order_product_mapping.all()\
                .values('product__id').annotate(shipped_items=Sum('shipped_qty'))
            total_shipped_qty = form.instance.order.rt_order_order_product\
                .aggregate(total_shipped_qty=Sum('rt_order_product_order_product_mapping__shipped_qty'))\
                .get('total_shipped_qty')
            total_ordered_qty = form.instance.order.ordered_cart.rt_cart_list\
                .aggregate(total_ordered_qty=Sum('no_of_pieces'))\
                .get('total_ordered_qty')

            update_order_status_picker_reserve_qty.delay(
                form.instance.id, form.cleaned_data.get('close_order'),
                list(shipment_products_dict), total_shipped_qty,
                total_ordered_qty)

    def get_queryset(self, request):
        order_config = GlobalConfig.objects.filter(key='plan_shipment_month').last()
        to_date = datetime.date.today() + datetime.timedelta(days=1)
        from_date = to_date + relativedelta(months=-(order_config.value))
        qs = super(ShipmentAdmin, self).get_queryset(request).filter(
            created_at__lte=to_date, created_at__gte=from_date)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_shop__shop_owner=request.user)
                ).filter(
            created_at__lte=to_date, created_at__gte=from_date)


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
        list_display = ('created_at', 'dispatch_no', 'total_trip_shipments', 'trip_amount')
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
        'dispathces', 'total_trip_shipments', 'delivery_boy', 'seller_shop', 'vehicle_no',
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

    # def trip_weight(self, obj):
    #     return obj.trip_weight()
    # trip_weight.short_description = 'Trip Weight (Kg)'

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
    actions = ["export_as_csv_commercial",]
    list_display = (
        'dispatch_no', 'trip_amount', 'cash_to_be_collected', 'download_trip_pdf', 'delivery_boy',
        'vehicle_no', 'trip_status', 'starts_at', 'completed_at',
        'seller_shop',)
    list_display_links = ('dispatch_no', )
    list_per_page = 25
    list_max_show_all = 100
    list_select_related = ('delivery_boy', 'seller_shop')
    readonly_fields = ('dispatch_no','trip_amount', 'delivery_boy', 'seller_shop',
                        'total_received_amount', 'vehicle_no', 'starts_at', 'trip_amount',
                       #'received_cash_amount', 'received_online_amount',
                       'completed_at', 'e_way_bill_no', 'cash_to_be_collected')
    autocomplete_fields = ('seller_shop',)
    search_fields = [
        'delivery_boy__first_name', 'delivery_boy__last_name',
        'delivery_boy__phone_number', 'vehicle_no', 'dispatch_no',
        'seller_shop__shop_name'
    ]
    fields = ['trip_status', 'cash_to_be_collected', #'description',
                'dispatch_no', 'total_received_amount',
              #'received_cash_amount', 'received_online_amount',
              'delivery_boy', 'seller_shop', 'starts_at', 'completed_at',
              'e_way_bill_no', 'vehicle_no']

    list_filter = ['trip_status', ('created_at', DateTimeRangeFilter),
                   ('starts_at', DateTimeRangeFilter), DeliveryBoySearch,
                   ('completed_at', DateTimeRangeFilter), VehicleNoSearch,
                   DispatchNoSearch]
    form = CommercialForm

    def cash_to_be_collected(self, obj):
        return obj.cash_to_be_collected()
    cash_to_be_collected.short_description = 'Amount to be Collected'

    def total_received_amount(self, obj):
        if obj.total_received_amount:
            return obj.total_received_amount
        else:
            return 0
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
            return qs.filter(trip_status__in=[Trip.RETURN_VERIFIED, Trip.PAYMENT_VERIFIED])
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user),
            trip_status__in=[Trip.RETURN_VERIFIED, Trip.PAYMENT_VERIFIED])

    def download_trip_pdf(self, obj):
        return format_html("<a href= '%s' >Download Trip PDF</a>"%(reverse('download_trip_pdf', args=[obj.pk])))
    download_trip_pdf.short_description = 'Trip Details'


class NoteAdmin(admin.ModelAdmin):
    list_display = ('credit_note_id', 'shipment', 'shop', 'note_amount','download_credit_note','created_at')
    fields = ('credit_note_id', 'shop', 'shipment', 'note_type', 'note_amount',
              'invoice_no', 'status')
    readonly_fields = ('credit_note_id', 'shop', 'shipment', 'note_type',
                       'note_amount', 'invoice_no', 'status')
    list_filter = [('created_at', DateTimeRangeFilter),ShipmentSearch, CreditNoteSearch, ShopSearch]

    search_fields = ('credit_note_id','shop__shop_name', 'shipment__invoice__invoice_no')
    list_per_page = 50
    # def note_amount(self, obj):
    #     pp = OrderedProductMapping.objects.filter(ordered_product=obj.shipment.id)
    #     shipment_cancelled = True if obj.shipment.shipment_status == 'CANCELLED' else False
    #     products = pp
    #     sum_amount = 0
    #     if obj.credit_note_type == 'DISCOUNTED':
    #         for m in products:
    #             sum_amount = sum_amount + (int(m.delivered_qty) * (m.price_to_retailer-m.discounted_price))
    #     else:
    #         if shipment_cancelled:
    #             for m in products:
    #                 sum_amount = sum_amount + (int(m.shipped_qty) * (m.price_to_retailer))
    #
    #         else:
    #             for m in products:
    #                 sum_amount = sum_amount + (int(m.returned_qty + m.returned_damage_qty) * (m.price_to_retailer))
    #         return sum_amount

    # note_amount.short_description = 'Note Amount'

    class Media:
        pass

    def download_credit_note(self, obj):
        if obj.credit_note_type == 'RETURN':
            return format_html(
                        "<a href= '%s' >Download Credit Note</a>" %
                           (reverse('download_credit_note', args=[obj.pk]))
            )
        elif obj.credit_note_type=='DISCOUNTED':
            return format_html(
                        "<a href= '%s' >Download Credit Note</a>" %
                            (reverse('discounted_credit_note', args=[obj.pk]))
            )
        else:
            return format_html(
                "<a href= '%s' >Download Credit Note</a>" %
                (reverse('download_credit_note', args=[obj.pk]))
            )

    download_credit_note.short_description = 'Download Credit Note'


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


class InvoiceAdmin(admin.ModelAdmin):
    actions = ['invoice_data_excel_action', 'download_bulk_invoice']
    list_display = ('invoice_no', 'created_at', 'get_invoice_amount', 'get_shipment_status',
                    'get_order', 'get_order_date', 'get_order_status', 'get_shipment',
                    'get_trip_no', 'get_trip_status', 'get_trip_started_at',
                    'get_trip_completed_at', 'get_paid_amount', 'get_cn_amount')
    list_per_page = FIFTY
    fieldsets = (
        ('Invoice', {
            'fields': (('invoice_no', 'get_invoice_amount'), ('created_at', 'invoice_pdf'))
        }),
        ('Shipment', {
            'classes': ('extrapretty',),
            'fields': (('get_shipment_status', 'get_shipment'),),
        }),
        ('Trip', {
            'classes': ('extrapretty',),
            'fields': (('get_trip_no', 'get_trip_status'),),
        }),
        ('Order', {
            'classes': ('extrapretty',),
            'fields': ('get_order',),
        }),
    )
    readonly_fields = ('invoice_no', 'get_shipment', 'invoice_pdf')
    search_fields =('invoice_no', 'shipment__trip__dispatch_no', 'shipment__order__order_no')
    ordering = ('-created_at', )
    list_filter = (
        InvoiceAdminOrderFilter, InvoiceAdminTripFilter,
        ('created_at', InvoiceCreatedAt),
        ('shipment__trip__starts_at', DeliveryStartsAt),
        ('shipment__trip__completed_at', DeliveryCompletedAt),
        ('shipment__order__created_at', OrderCreatedAt))

    def invoice_data_excel_action(self, request, queryset):
        return create_invoice_data_excel(request, queryset, RoundAmount,
                                         ShipmentPayment, OrderedProduct, Trip,
                                         Order)
    invoice_data_excel_action.short_description = "Download CSV of selected Invoices"

    def download_bulk_invoice(self, request, *args, **kwargs):
        """

        :param request: request params
        :param args: argument list
        :param kwargs: keyword argument
        :return: response
        """

        if len(args[0]) <= FIFTY:
            # argument_list contains list of pk exclude shipment created and blank invoice
            argument_list = []
            for arg in args[ZERO]:
                if len(args[0]) <= 1 and (
                        arg.shipment_status == OrderedProduct.SHIPMENT_STATUS[ZERO] or arg.invoice_no == '-'):
                    error_message = messages.error(request, ERROR_MESSAGES["4002"])
                    return error_message
                elif arg.shipment_status == OrderedProduct.SHIPMENT_STATUS[ZERO] or arg.invoice_no == '-':
                    pass
                else:
                    # append pk which are not falling under the shipment created and blank invoice number
                    argument_list.append(arg.shipment.pk)
            # call get method under the DownloadInvoiceSP class
            response = DownloadInvoiceSP.get(self, request, argument_list, **kwargs)
            if response[1] is True:
                return redirect(response[0])
            else:
                return response[0]
        else:
            response = messages.error(request, ERROR_MESSAGES["4001"])
        return response

    # download bulk invoice short description
    download_bulk_invoice.short_description = DOWNLOAD_BULK_INVOICE

    class Media:
        js = ('admin/js/picker.js',)

    def get_invoice_amount(self, obj):
        return "%s %s" % (u'\u20B9', str(obj.invoice_amount))
    get_invoice_amount.short_description = "Invoice Amount"

    def get_shipment(self, obj):
        url = reverse('admin:%s_%s_change' % (obj._meta.app_label, 'orderedproduct'),  args=[obj.shipment_id] )
        return format_html("<a href='%s' target='blank'>View Shipment Details</a>" % (url))
    get_shipment.short_description = "Shipment"

    def get_order(self, obj):
        return obj.get_order
    get_order.short_description = "Order"

    def get_shipment_status(self, obj):
        if obj.shipment_status:
            shipment_status = dict(OrderedProduct.SHIPMENT_STATUS)
            return shipment_status[obj.shipment_status]
        return "-"
    get_shipment_status.short_description = "Shipment Status"

    def get_trip_no(self, obj):
        return obj.trip_no
    get_trip_no.short_description = "Trip"

    def get_trip_status(self, obj):
        if obj.trip_status:
            trip_status = dict(Trip.TRIP_STATUS)
            return trip_status[obj.trip_status]
        return "-"
    get_trip_status.short_description = "Trip Status"

    def get_order_date(self, obj):
        return obj.order_date
    get_order_date.short_description = "Order Date"

    def get_order_status(self, obj):
        if obj.order_status:
            order_status = dict(Order.ORDER_STATUS)
            return order_status[obj.order_status]
        return "-"
    get_order_status.short_description = "Order Status"

    def get_trip_started_at(self, obj):
        return obj.trip_started_at
    get_trip_started_at.short_description = "Delivery Started At"

    def get_trip_completed_at(self, obj):
        return obj.trip_completed_at
    get_trip_completed_at.short_description = "Delivery Completed At"

    def get_paid_amount(self, obj):
        return obj.shipment_paid_amount
    get_paid_amount.short_description = "Paid Amount"

    def get_cn_amount(self, obj):
        return obj.cn_amount
    get_cn_amount.short_description = "CN Amount"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        shipment_payments = ShipmentPayment.objects.filter(shipment__invoice__id=OuterRef('pk')).order_by().values('shipment__invoice__id')
        shipment_paid_amount = shipment_payments.annotate(sum=Sum('paid_amount')).values('sum')
        credit_notes = Note.objects.filter(shipment__invoice__id=OuterRef('pk')).order_by().values('shipment__invoice__id')
        credit_notes_amount = credit_notes.annotate(sum=Sum('amount')).values('sum')
        qs = qs.annotate(
            get_order=F('shipment__order__order_no'), shipment_status=F('shipment__shipment_status'),
            trip_no=F('shipment__trip__dispatch_no'), trip_status=F('shipment__trip__trip_status'),
            order_date=F('shipment__order__created_at'), order_status=F('shipment__order__order_status'),
            trip_started_at=F('shipment__trip__starts_at'), trip_completed_at=F('shipment__trip__completed_at'),
            shipment_paid_amount=Subquery(shipment_paid_amount),
            cn_amount=Subquery(credit_notes_amount))
        return qs

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SQSum(Subquery):
    """
    Subclass of subquery get the sum
    """
    template = '(SELECT SUM(%(field)s) FROM (%(subquery)s) _sum)'

    def as_sql(self, compiler, connection, template=None, **extra_context):
        if 'field' not in extra_context and 'field' not in self.extra:
            if len(self.queryset._fields) > 1:
                raise FieldError('You must provide the field name, or have a single column')
            extra_context['field'] = self.queryset._fields[0]
        return super(SQSum, self).as_sql(
            compiler, connection, template=template, **extra_context
        )

class DeliveryPerformanceDashboard(admin.ModelAdmin):
    """
    Admin class for representing Delivery Performance Dashboard
    """
    # change_list_template = 'admin/retailer_to_sp/delivery_performance_change_list.html'
    list_display = ['dispathces', 'delivery_boy', 'delivered_cnt', 'returned_cnt', 'pending_cnt', 'rescheduled_cnt',
                    'total_shipments', 'delivery_percent', 'returned_percent', 'rescheduled_percent', 'invoice_amount',
                    'delivered_amount', 'delivered_value_percent',
                    'starts_at', 'completed_at', 'opening_kms', 'closing_kms', 'km_run']
    list_filter = [ DeliveryBoySearch, VehicleNoSearch, DispatchNoSearch, ('created_at', DateTimeRangeFilter)]
    actions = ['export_as_csv']

    def delivered_cnt(self, obj):
        return obj.delivered_cnt

    def returned_cnt(self, obj):
        return obj.returned_cnt

    def pending_cnt(self, obj):
        return obj.pending_cnt

    def rescheduled_cnt(self, obj):
        return obj.rescheduled_cnt

    def total_shipments(self, obj):
        return obj.total_shipments

    def invoice_amount(self, obj):
        return obj.invoice_amount

    def delivered_amount(self, obj):
        return obj.delivered_amount

    def delivery_percent(self, obj):
        return self.get_percent(obj.delivered_cnt, obj.total_shipments)

    def get_percent(self, part, whole):
        return round(part / whole * 100) if whole and whole>0 else 0

    def returned_percent(self, obj):
        return self.get_percent(obj.returned_cnt, obj.total_shipments)

    def rescheduled_percent(self, obj):
        return self.get_percent(obj.rescheduled_cnt, obj.total_shipments)

    def delivered_value_percent(self, obj):
        return self.get_percent(obj.delivered_amount, obj.invoice_amount)

    def km_run(self, obj):
        return obj.closing_kms-obj.opening_kms if obj.closing_kms and obj.opening_kms else 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def dispathces(self, obj):
        return mark_safe("<a href='/admin/retailer_to_sp/cart/trip-planning/%s/change/'>%s<a/>" % (obj.pk,
                                                                                                   obj.dispatch_no))

    def get_queryset(self, request):

        qs = super(DeliveryPerformanceDashboard, self).get_queryset(request)
        #today = datetime.datetime.now().date()
        #start_from = today-datetime.timedelta(days=60)
        to_date, from_date = self.get_date(request)
        qs = qs.filter(created_at__gte=from_date, created_at__lte=to_date)

        metrics = {
            'invoice_amount': Sum(F('rt_invoice_trip__rt_order_product_order_product_mapping__effective_price') *
                                  F('rt_invoice_trip__rt_order_product_order_product_mapping__shipped_qty'), output_field=FloatField()),
            'delivered_amount': Sum(F('rt_invoice_trip__rt_order_product_order_product_mapping__effective_price') *
                                    F('rt_invoice_trip__rt_order_product_order_product_mapping__delivered_qty'), output_field=FloatField())
        }
        delivered_status_list = ['PARTIALLY_DELIVERED_AND_COMPLETED', 'FULLY_DELIVERED_AND_COMPLETED',
                                 'PARTIALLY_DELIVERED_AND_VERIFIED', 'FULLY_DELIVERED_AND_VERIFIED',
                                 'PARTIALLY_DELIVERED_AND_CLOSED', 'FULLY_DELIVERED_AND_CLOSED']
        returned_status_list = ['FULLY_RETURNED_AND_COMPLETED', 'FULLY_RETURNED_AND_VERIFIED',
                                'FULLY_RETURNED_AND_CLOSED']
        pending_status_list = ['OUT_FOR_DELIVERY']

        qs = qs.annotate(**metrics,
                         delivered_cnt=Count('rt_invoice_trip', filter=Q(rt_invoice_trip__shipment_status__in=delivered_status_list)),
                         returned_cnt=Count('rt_invoice_trip', filter=Q(rt_invoice_trip__shipment_status__in=returned_status_list)),
                         pending_cnt=Count('rt_invoice_trip', filter=Q(rt_invoice_trip__shipment_status__in=pending_status_list)),
                         rescheduled_cnt=Count('rescheduling_shipment_trip'),
                         total_shipments=Count('rt_invoice_trip')
                         ).order_by('-id').prefetch_related('delivery_boy')
        return qs

    def get_date(self, request):
        try:
            if request.GET['created_at__lte_0'] is None:
                to_date = datetime.date.today() + datetime.timedelta(days=1)
            else:
                to_date = request.GET['created_at__lte_0']
        except:
            to_date = datetime.date.today() + datetime.timedelta(days=1)
        try:
            if request.GET['created_at__gte_0'] is None:
                from_date = to_date + relativedelta(days=-(1))
            else:
                from_date = request.GET['created_at__gte_0']
        except:
            from_date = to_date + relativedelta(days=-(1))
        return to_date, from_date

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        list_display = ('dispathces', 'delivery_boy', 'delivered_cnt', 'returned_cnt', 'pending_cnt', 'rescheduled_cnt',
                        'total_shipments', 'delivery_percent', 'returned_percent', 'rescheduled_percent', 'invoice_amount',
                        'delivered_amount', 'delivered_value_percent',
                        'starts_at', 'completed_at', 'opening_kms', 'closing_kms', 'km_run')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            writer.writerow([obj.dispatch_no, obj.delivery_boy, obj.delivered_cnt, obj.returned_cnt,
                             obj.rescheduled_cnt, obj.total_shipments, self.delivery_percent(obj),
                             self.returned_percent(obj), self.rescheduled_percent(obj), obj.invoice_amount,
                             obj.delivered_amount, self.delivered_value_percent(obj), obj.starts_at, obj.completed_at,
                             obj.opening_kms, obj.closing_kms, self.km_run(obj)])
        return response


class PickerPerformancePickerBoyFilter(InputFilter):
    title = 'Picker Boy'
    parameter_name = 'phone_no'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(
                  Q(picker_boy__phone_number=value)
                )
        return queryset

class PickerPerformanceDashboard(admin.ModelAdmin):
    """
    Admin class for representing Delivery Performance Dashboard
    """
    list_filter = [PickerPerformancePickerBoyFilter, ('picker_assigned_date', DateTimeRangeFilter)]
    list_display = ('picker_number', 'full_name', 'assigned_order_count', 'order_amount', 'invoice_amount', 'fill_rate',
                    'picked_order_count', 'picked_sku_count', 'picked_pieces_count',)
    actions = ['export_as_csv']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @staticmethod
    def picker_number(obj):
        try:
            return obj.picker_boy.phone_number
        except Exception as e:
            logger.exception(e)
            return ''

    @staticmethod
    def full_name(obj):
        try:
            return obj.picker_boy.get_full_name()
        except Exception as e:
            logger.exception(e)
            return ''


    def assigned_order_count(self, obj):
        try:
            return obj.picker_boy.picker_user.filter(picker_assigned_date__date__gte=obj.from_date,picker_assigned_date__date__lte=obj.to_date).count()
        except Exception as e:
            logger.exception(e)
            return 0

    def order_amount(self, obj):
        try:
            return obj.picker_boy.picker_user.filter(picker_assigned_date__date__gte=obj.from_date,picker_assigned_date__date__lte=obj.to_date).aggregate(Sum('order__order_amount'))['order__order_amount__sum']
        except Exception as e:
            logger.exception(e)
            return 0

    def invoice_amount(self, obj):
        try:
            return obj.picker_boy.picker_user.filter(picker_assigned_date__date__gte=obj.from_date,picker_assigned_date__date__lte=obj.to_date).aggregate(inv_amount=Sum(
                F('order__rt_order_order_product__rt_order_product_order_product_mapping__effective_price')
                *
                F('order__rt_order_order_product__rt_order_product_order_product_mapping__shipped_qty'),
                output_field=FloatField()))['inv_amount']

        except Exception as e:
            logger.exception(e)
            return 0

    def get_percent(self, part, whole):
        return "{:.2f}".format((1-(part / whole))*100) if whole and whole>0 else 0

    def fill_rate(self, obj):
        try:
            fill_rate = self.get_percent(self.invoice_amount(obj), self.order_amount(obj))
        except:
            fill_rate = 0
        return fill_rate

    def picked_order_count(self, obj):
        try:
            return obj.picker_boy.picker_user.filter(picker_assigned_date__date__gte=obj.from_date,
                                              picker_assigned_date__date__lte=obj.to_date,
                                              picking_status='picking_complete').count()
        except Exception as e:
            logger.exception(e)
            return 0

    def picked_sku_count(self, obj):
        try:
            qs = obj.picker_boy.picker_user.filter(picker_assigned_date__date__gte=obj.from_date,picker_assigned_date__date__lte=obj.to_date, picking_status='picking_complete')
            picked_count = Pickup.objects.filter(pickup_type_id__in=qs.values_list('order__order_no', flat=True)).count()
            return picked_count
        except:
            return 0

    def picked_pieces_count(self, obj):
        try:
            qs = obj.picker_boy.picker_user.filter(picker_assigned_date__date__gte=obj.from_date,
                                                   picker_assigned_date__date__lte=obj.to_date,
                                                   picking_status='picking_complete')

            picked_quantity = Pickup.objects.filter(pickup_type_id__in=qs.values_list('order__order_no', flat=True)
                                                  ).aggregate(Sum('pickup_quantity'))['pickup_quantity__sum']
            return picked_quantity

        except Exception as e:
            logger.exception(e)
            return 0


    def get_queryset(self, request):
        """
        request object
        return:-queryset
        """

        to_date, from_date = self.get_date(request)
        qs = super(PickerPerformanceDashboard, self).get_queryset(request)
        queryset = qs.filter(
            picker_assigned_date__date__lte=to_date, picker_assigned_date__date__gte=from_date).order_by(
            'picker_boy').distinct('picker_boy').select_related('order').prefetch_related('order__rt_order_order_product',
                                                                                         'order__rt_order_order_product__rt_order_product_order_product_mapping').prefetch_related('picker_boy__picker_user').annotate(to_date=Value(to_date, output_field=CharField()), from_date=Value(from_date, output_field=CharField()))
        return queryset

    def get_date(self, request):
        try:
            if request.GET['picker_assigned_date__lte_0'] is None:
                to_date = datetime.date.today() + datetime.timedelta(days=1)
            else:
                to_date = request.GET['picker_assigned_date__lte_0']
        except:
            to_date = datetime.date.today() + datetime.timedelta(days=1)
        try:
            if request.GET['picker_assigned_date__gte_0'] is None:
                from_date = to_date + relativedelta(days=-(1))
            else:
                from_date = request.GET['picker_assigned_date__gte_0']
        except:
            from_date = to_date + relativedelta(days=-(1))
        return to_date, from_date

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        list_display = ('picker_number','full_name', 'assigned_order_count','order_amount','invoice_amount','fill_rate',
                    'picked_order_count', 'picked_sku_count','picked_pieces_count')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(list_display)
        for obj in queryset:
            writer.writerow([self.picker_number(obj), self.full_name(obj), self.assigned_order_count(obj),
                             self.order_amount(obj), self.invoice_amount(obj), self.fill_rate(obj),
                             self.picked_order_count(obj), self.picked_sku_count(obj),
                             self.picked_pieces_count(obj)])
        return response

admin.site.register(Cart, CartAdmin)
admin.site.register(BulkOrder, BulkOrderAdmin)
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
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(DeliveryData, DeliveryPerformanceDashboard)
admin.site.register(PickerPerformance, PickerPerformanceDashboard)