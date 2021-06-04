import logging
import datetime
import math

from dal import autocomplete
from django import forms
from django.db.models import Sum, F, Q
from django.db import models
from django.contrib import messages, admin
from django.forms import Textarea
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.urls import reverse
from daterange_filter.filter import DateRangeFilter
from django.http import HttpResponseRedirect

from retailer_backend.filters import (BrandFilter, SupplierStateFilter, SupplierFilter, OrderSearch, QuantitySearch,
                                      InvoiceNoSearch, GRNSearch, POAmountSearch, PORaisedBy, ProductNameSearch,
                                      ProductSKUSearch, SupplierNameSearch, POCreatedBySearch, PONumberSearch)
from retailer_backend.messages import SUCCESS_MESSAGES, ERROR_MESSAGES
from products.models import ProductVendorMapping, ParentProduct
from barCodeGenerator import barcodeGen, merged_barcode_gen
from .views import DownloadPurchaseOrder, GetMessage
from .common_functions import upload_cart_product_csv, moving_average_buying_price
from .models import (Order, Cart, CartProductMapping, GRNOrder, GRNOrderProductMapping, BrandNote, PickList, Document,
                     PickListItems, OrderedProductReserved, Po_Message)
from .forms import (OrderForm, CartProductMappingForm, GRNOrderProductForm, GRNOrderProductFormset, DocumentFormset,
                    POGenerationAccountForm, POGenerationForm, DocumentForm)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    autocomplete_fields = ('cart_product',)
    search_fields = ('cart_product',)
    form = CartProductMappingForm

    cart_parent_product = forms.ModelChoiceField(
        queryset=ParentProduct.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='parent-product-autocomplete',
            attrs={
                "onChange": 'getLastGrnProductDetails(this)'
            },
            forward=['supplier_name']
        )
    )

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',  # jquery
            'admin/js/po_generation_form.js'
        )

    fields = ('cart_parent_product', 'cart_product', 'mrp', 'sku', 'tax_percentage', 'case_sizes', 'no_of_cases',
              'no_of_pieces', 'brand_to_gram_price_units', 'price', 'sub_total')
    readonly_fields = ('tax_percentage', 'mrp', 'sku', 'case_sizes', 'brand_to_gram_price_units', 'sub_total')

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return 'tax_percentage', 'mrp', 'sku', 'case_sizes', 'sub_total', 'brand_to_gram_price_units'
        elif request.user.has_perm('gram_to_brand.can_approve_and_disapprove'):
            return 'tax_percentage', 'mrp', 'sku', 'case_sizes', 'sub_total', 'brand_to_gram_price_units'
        return 'tax_percentage', 'mrp', 'sku', 'case_sizes', 'sub_total', 'brand_to_gram_price_units'


class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'po_status', 'last_modified_by')
    autocomplete_fields = ('brand',)
    list_filter = [BrandFilter, SupplierStateFilter, SupplierFilter, ('po_creation_date', DateRangeFilter),
                   ('po_validity_date', DateRangeFilter), POAmountSearch, PORaisedBy, PONumberSearch]
    form = POGenerationForm
    list_display_links = None

    def get_queryset(self, request):
        qs = super(CartAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.has_perm('gram_to_brand.can_approve_and_disapprove'):
            return qs.exclude(po_status='OPEN')
        return qs.filter(
            Q(gf_shipping_address__shop_name__related_users=request.user) |
            Q(gf_shipping_address__shop_name__shop_owner=request.user)
        ).exclude(po_status='PDA')

    def download_purchase_order(self, obj):
        return format_html("<a href= '%s' >Download PO</a>" % (reverse('admin:download_purchase_order', args=[obj.pk])))

    download_purchase_order.short_description = 'Download Purchase Order'

    def get_list_display(self, request):

        def po_edit_link(obj):
            # if request.user.is_superuser:
            #     return format_html("<a href= '/admin/gram_to_brand/cart/%s/change/' >%s</a>" % (obj.pk, obj.po_no))
            # if request.user.has_perm('gram_to_brand.can_create_po'):
            #     return format_html("%s" % obj.po_no)
            return format_html("<a href= '/admin/gram_to_brand/cart/%s/change/' >%s</a>" % (obj.pk, obj.po_no))

        po_edit_link.short_description = 'Po No'

        return [po_edit_link, 'brand', 'supplier_state', 'supplier_name', 'po_creation_date', 'po_validity_date',
                'po_raised_by', 'po_status', 'po_delivery_date', 'approved_by', 'download_purchase_order']

    def save_formset(self, request, form, formset, change):
        obj = form.instance
        get_po_msg = Po_Message.objects.create(message=request.POST.get('message'),
                                               created_by=request.user) if request.POST.get('message') else None
        flag, obj.po_status, is_approved = self.po_status_request(request, obj)
        obj.po_message = get_po_msg
        if obj.po_raised_by is None:
            obj.po_raised_by = request.user
        obj.last_modified_by = request.user
        if is_approved:
            obj.approved_by = request.user
            obj.approved_at = datetime.datetime.now()
        obj.save()
        if flag:
            self.log_entry(request.user.pk, obj)
        formset.save()
        if 'cart_product_mapping_csv' in form.changed_data:
            upload_cart_product_csv(obj)
        return HttpResponseRedirect("/admin/gram_to_brand/cart/")

    @staticmethod
    def log_entry(user_id, obj):
        LogEntry.objects.log_action(
            user_id=user_id,
            content_type_id=ContentType.objects.get_for_model(obj).pk,
            object_id=obj.pk,
            action_flag=ADDITION,
            object_repr='',
            change_message=SUCCESS_MESSAGES['CHANGED_STATUS'] % obj.get_po_status_display(),
        )

    @staticmethod
    def po_status_request(request, obj):
        flag = True
        is_approved = False
        status = obj.po_status
        if "_approve" in request.POST:
            status = obj.OPEN
            is_approved = True
        elif "_disapprove" in request.POST:
            status = obj.DISAPPROVED
        elif "_approval_await" in request.POST:
            status = obj.PENDING_APPROVAL
        elif "_close" in request.POST:
            status = obj.PARTIAL_DELIVERED_CLOSE
        elif status is None:
            status = obj.OPEN
        return flag, status, is_approved

    class Media:
        js = (
            '/ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',  # jquery
            'admin/js/po_generation_form.js'
        )

    def get_urls(self):
        from django.conf.urls import url
        urls = super(CartAdmin, self).get_urls()
        urls = [
                   url(r'^download-purchase-order/(?P<pk>\d+)/purchase_order/$',
                       self.admin_site.admin_view(DownloadPurchaseOrder.as_view()),
                       name='download_purchase_order'),
                   url(r'^message-list/$',
                       self.admin_site.admin_view(GetMessage.as_view()),
                       name='message-list'),
               ] + urls
        return urls

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 33})},
    }

    def get_readonly_fields(self, request, obj=None):
        return 'po_status',

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if request.user.is_superuser:
            defaults['form'] = POGenerationForm
        elif obj is not None and obj.cart_type == Cart.CART_TYPE_CHOICE.AUTO and \
                request.user.has_perm('gram_to_brand.can_approve_and_disapprove'):
            defaults['form'] = POGenerationAccountForm
        else:
            defaults['form'] = POGenerationForm
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)


class GRNOrderForm(forms.ModelForm):
    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        widget=autocomplete.ModelSelect2(url='order-autocomplete', )
    )

    class Meta:
        model = GRNOrder
        fields = ('order', 'invoice_no',)


class DocumentAdmin(admin.StackedInline):
    model = Document
    formset = DocumentFormset
    form = DocumentForm
    fields = ('document_number', 'document_image')
    extra = 1


class GRNOrderProductMappingAdmin(admin.TabularInline):
    model = GRNOrderProductMapping
    formset = GRNOrderProductFormset
    form = GRNOrderProductForm

    fields = ('product', 'product_mrp', 'po_product_quantity', 'po_product_price', 'already_grned_product',
              'already_returned_product', 'product_invoice_price', 'manufacture_date', 'expiry_date',
              'best_before_year', 'best_before_month', 'product_invoice_qty', 'delivered_qty', 'returned_qty',
              'download_batch_id_barcode', 'show_batch_id',)
    exclude = ('last_modified_by', 'available_qty',)
    readonly_fields = ('download_batch_id_barcode', 'show_batch_id')
    extra = 0
    ordering = ['product__product_name']
    template = 'admin/gram_to_brand/grn_order/tabular.html'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('product_mrp', 'po_product_quantity', 'po_product_price',
                                           'already_grned_product', 'already_returned_product')
        return self.readonly_fields

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(GRNOrderProductMappingAdmin, self).get_formset(request, obj, **kwargs)
        cart_id = request.GET.get('cart')
        if cart_id:
            formset.order = Cart.objects.get(pk=int(cart_id))
        return formset

    def download_batch_id_barcode(self, obj):
        if obj.batch_id is None:
            return format_html("-")
        if obj.barcode_id is None:
            product_id = str(obj.product_id).zfill(5)
            expiry_date = datetime.datetime.strptime(str(obj.expiry_date), '%Y-%m-%d').strftime('%d%m%y')
            barcode_id = str("2" + product_id + str(expiry_date))
        else:
            barcode_id = obj.barcode_id
        return format_html("<a href= '{0}' >{1}</a>".format(reverse('batch_barcodes', args=[obj.pk]), barcode_id))

    def show_batch_id(self, obj):
        return format_html(obj.batch_id) if obj.batch_id else format_html("-")

    show_batch_id.short_description = 'Batch ID'
    download_batch_id_barcode.short_description = 'Download Barcode'


class BrandNoteAdmin(admin.ModelAdmin):
    model = BrandNote
    list_display = ('brand_note_id', 'grn_order', 'amount')
    exclude = ('brand_note_id', 'last_modified_by',)


class OrderItemAdmin(admin.ModelAdmin):
    list_filter = [OrderSearch, QuantitySearch, PORaisedBy, ('order__ordered_cart__po_creation_date', DateRangeFilter)]
    list_display = ('order', 'ordered_product', 'ordered_qty', 'total_delivered_qty', 'total_damaged_qty',
                    'po_creation_date', 'item_status',)

    def po_creation_date(self, obj):
        return "%s" % obj.order.ordered_cart.po_creation_date

    po_creation_date.short_description = 'Po Creation Date'


class GRNOrderAdmin(admin.ModelAdmin):
    inlines = [DocumentAdmin, GRNOrderProductMappingAdmin]
    autocomplete_fields = ('order',)
    exclude = ('order_item', 'grn_id', 'last_modified_by',)
    actions = ['download_barcode']
    list_per_page = 50
    list_display = ('grn_id', 'order', 'invoice_no', 'grn_date', 'brand', 'supplier_state', 'supplier_name',
                    'po_status', 'po_created_by', 'download_debit_note')
    list_filter = [OrderSearch, InvoiceNoSearch, GRNSearch, ProductNameSearch, ProductSKUSearch, SupplierNameSearch,
                   POCreatedBySearch, ('created_at', DateRangeFilter),
                   ('grn_order_grn_order_product__expiry_date', DateRangeFilter)]
    form = GRNOrderForm
    fields = ('order', 'invoice_no', 'invoice_date', 'invoice_amount', 'tcs_amount')

    class Media:
        js = ('admin/js/picker.js',)

    def po_created_by(self, obj):
        return obj.order.ordered_cart.po_raised_by

    po_created_by.short_description = 'PO Created By'

    def brand(self, obj):
        return obj.order.ordered_cart.brand

    brand.short_description = 'Brand'

    def supplier_state(self, obj):
        return obj.order.ordered_cart.supplier_state

    supplier_state.short_description = 'Supplier State'

    def supplier_name(self, obj):
        return obj.order.ordered_cart.supplier_name

    supplier_name.short_description = 'Supplier Name'

    def po_status(self, obj):
        return obj.order.ordered_cart.get_po_status_display()

    po_status.short_description = 'Po Status'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('order',)
        return self.readonly_fields

    def get_queryset(self, request):
        qs = super(GRNOrderAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(Q(order__ordered_cart__gf_shipping_address__shop_name__related_users=request.user) |
                         Q(order__ordered_cart__gf_shipping_address__shop_name__shop_owner=request.user))

    def download_debit_note(self, obj):
        if obj.grn_order_brand_note.count() > 0 and obj.grn_order_brand_note.filter(status=True):
            return format_html(
                "<a href= '%s' >Download Debit Note</a>" % (reverse('download_debit_note', args=[obj.pk])))

    download_debit_note.short_description = 'Download Debit Note'
    change_list_template = 'admin/gram_to_brand/order/change_list.html'

    def save_related(self, request, form, formsets, change):
        flag = 'DLVR'
        super(GRNOrderAdmin, self).save_related(request, form, formsets, change)
        obj = form.instance
        obj.order.ordered_cart.cart_list.values('cart_product', 'no_of_pieces')
        grn_list_map = {int(i['product']): (i['delivered_qty_sum'], i['returned_qty_sum'],
                                            i['product_invoice_price'], i['vendor_product__brand_to_gram_price_unit'],
                                            i['vendor_product__case_size'], i['product__repackaging_type'],
                                            i['grn_order__order__ordered_cart__gf_shipping_address__shop_name'],
                                            i['id']
                                            ) for i in
                        GRNOrderProductMapping.objects.filter(
                            grn_order__order=obj.order).values('product',
                                                               'product_invoice_price',
                                                               'vendor_product__brand_to_gram_price_unit',
                                                               'vendor_product__case_size',
                                                               'product__repackaging_type',
                                                               'grn_order__order__ordered_cart__gf_shipping_address__shop_name',
                                                               'id'
                                                               )
                            .annotate(delivered_qty_sum=Sum(F('delivered_qty')))
                            .annotate(returned_qty_sum=Sum(F('returned_qty')))}
        returned_qty_totalsum = GRNOrderProductMapping.objects.filter(grn_order__order=obj.order).aggregate(
            returned_qty_totalsum=Sum('returned_qty'))['returned_qty_totalsum']
        for product_price_map in obj.order.ordered_cart.cart_list.values('cart_product', 'no_of_pieces'):

            if returned_qty_totalsum > 0:
                flag = 'PDLC'
                if grn_list_map[product_price_map['cart_product']][0] == 0 and \
                        grn_list_map[product_price_map['cart_product']][1] >= 0:
                    flag = 'PARR'
                elif grn_list_map[product_price_map['cart_product']][0] + \
                        grn_list_map[product_price_map['cart_product']][1] != product_price_map['no_of_pieces']:
                    flag = 'PDLV'
                    break
            elif grn_list_map[product_price_map['cart_product']][0] != product_price_map['no_of_pieces']:
                flag = 'PDLV'
                break

        for product_price_map in obj.order.ordered_cart.cart_list.values('cart_product', 'no_of_pieces',
                                                                         '_tax_percentage'):
            # If delivered quantity, update moving buying price of product
            if grn_list_map[product_price_map['cart_product']][0] > 0:
                grn_product_data = grn_list_map[product_price_map['cart_product']]
                moving_average_buying_price(product_price_map['cart_product'], grn_product_data[7], grn_product_data[5],
                                            grn_product_data[2], grn_product_data[0], grn_product_data[6],
                                            grn_product_data[3], grn_product_data[4],
                                            product_price_map['_tax_percentage'])

        obj.order.ordered_cart.po_status = flag
        obj.order.ordered_cart.save()

    def download_barcode(self, request, queryset):
        """
        :param self:
        :param request:
        :param queryset:
        :return:
        """
        info_logger.info("download Barcode List for GRN method has been called.")
        bin_id_list = {}
        if queryset.count() > 1:
            response = messages.error(request, ERROR_MESSAGES['1003'])
            return response
        for obj in queryset:
            grn_product_list = GRNOrderProductMapping.objects.filter(grn_order=obj).all()
            for grn_product in grn_product_list:
                if grn_product.batch_id is None:
                    continue
                product_mrp = ProductVendorMapping.objects.filter(vendor=obj.order.ordered_cart.supplier_name,
                                                                  product=grn_product.product)
                barcode_id = grn_product.barcode_id
                if barcode_id is None:
                    product_id = str(grn_product.product_id).zfill(5)
                    expiry_date = datetime.datetime.strptime(str(grn_product.expiry_date), '%Y-%m-%d').strftime(
                        '%d%m%y')
                    barcode_id = str("2" + product_id + str(expiry_date))
                temp_data = {"qty": math.ceil(grn_product.delivered_qty / int(product_mrp.last().case_size)),
                             "data": {"SKU": grn_product.product.product_name,
                                      "Batch": grn_product.batch_id,
                                      "MRP": product_mrp.last().product_mrp if product_mrp.exists() else ''}}
                bin_id_list[barcode_id] = temp_data
        return merged_barcode_gen(bin_id_list)

    download_barcode.short_description = "Download Barcode List"


class OrderAdmin(admin.ModelAdmin):
    search_fields = ['order_no', ]
    list_display = ('order_no', 'brand', 'supplier_state', 'supplier_name', 'created_at', 'po_status', 'created_by',
                    'add_grn_link')
    form = OrderForm

    def created_by(self, obj):
        return obj.ordered_cart.po_raised_by

    created_by.short_description = 'Created By'

    def brand(self, obj):
        return obj.ordered_cart.brand

    brand.short_description = 'Brand'

    def supplier_state(self, obj):
        return obj.ordered_cart.supplier_state

    supplier_state.short_description = 'Supplier State'

    def supplier_name(self, obj):
        return obj.ordered_cart.supplier_name

    supplier_name.short_description = 'Supplier Name'

    def po_status(self, obj):
        return obj.ordered_cart.get_po_status_display()

    po_status.short_description = 'Po Status'

    def add_grn_link(self, obj):
        if obj.ordered_cart.po_status in [obj.ordered_cart.FINANCE_APPROVED, obj.ordered_cart.PARTIAL_DELIVERED,
                                          obj.ordered_cart.PARTIAL_RETURN, obj.ordered_cart.OPEN]:
            return format_html(
                "<a href = '/admin/gram_to_brand/grnorder/add/?order=%s&cart=%s' class ='addlink' > Add GRN</a>" %
                (obj.id, obj.ordered_cart.id))

    add_grn_link.short_description = 'Add GRN'

    change_list_template = 'admin/gram_to_brand/order/change_list.html'


class PickListItemAdmin(admin.TabularInline):
    model = PickListItems


class PickListAdmin(admin.ModelAdmin):
    inlines = [PickListItemAdmin]


class OrderedProductReservedAdmin(admin.ModelAdmin):
    list_display = ('order_product_reserved', 'cart', 'product', 'reserved_qty', 'order_reserve_end_time', 'created_at',
                    'reserve_status')


admin.site.register(PickList, PickListAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(OrderedProductReserved, OrderedProductReservedAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(GRNOrder, GRNOrderAdmin)
