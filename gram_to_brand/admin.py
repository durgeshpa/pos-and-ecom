from django.contrib import admin
from .models import (Order,Cart,CartProductMapping,GRNOrder,GRNOrderProductMapping,BrandNote,PickList,PickListItems,
                     OrderedProductReserved,Po_Message, Document)
from products.models import Product
from django import forms
from django.db.models import Sum, F
from django.utils.html import format_html
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from dal import autocomplete
from django.utils.html import format_html
from django.urls import reverse
from daterange_filter.filter import DateRangeFilter
from django.db.models import Q
from brand.models import Brand
from addresses.models import State,Address
from brand.models import Vendor
from shops.models import Shop
from gram_to_brand.forms import (OrderForm, CartProductMappingForm, GRNOrderForm, GRNOrderProductForm, GRNOrderProductFormset, POGenerationAccountForm)
from .forms import POGenerationForm
from django.http import HttpResponse, HttpResponseRedirect
from retailer_backend.filters import ( BrandFilter, SupplierStateFilter,SupplierFilter, OrderSearch, QuantitySearch, InvoiceNoSearch,
                                       GRNSearch, POAmountSearch, PORaisedBy)

from django.db.models import Q
from .views import DownloadPurchaseOrder, GetMessage
from django.db import models
from django.forms import Textarea
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
from retailer_backend.messages import SUCCESS_MESSAGES

class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    autocomplete_fields = ('cart_product',)
    search_fields =('cart_product',)
    form = CartProductMappingForm

    fields = ('cart_product','mrp','sku', 'tax_percentage','case_sizes', 'no_of_cases', 'no_of_pieces', 'price', 'sub_total')
    readonly_fields = ('tax_percentage','mrp','sku', 'case_sizes','sub_total')
    ##readonly_fields = ('tax_percentage','case_sizes','total_no_of_pieces',)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return 'tax_percentage', 'mrp','sku','case_sizes','sub_total'
        elif request.user.has_perm('gram_to_brand.can_approve_and_disapprove'):
            return 'tax_percentage', 'mrp','sku','case_sizes','sub_total'
            #return 'tax_percentage','case_sizes', 'no_of_cases', 'no_of_pieces', 'price', 'sub_total'
        return 'tax_percentage', 'mrp','sku','case_sizes','sub_total'

class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'po_status','last_modified_by')
    autocomplete_fields = ('brand',)
    #list_display = ('po_no','po_edit_link','brand','supplier_state','supplier_name', 'po_creation_date','po_validity_date','po_raised_by','po_status', 'download_purchase_order')
    list_filter = [BrandFilter,SupplierStateFilter ,SupplierFilter,('po_creation_date', DateRangeFilter),('po_validity_date', DateRangeFilter),POAmountSearch,PORaisedBy]
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
        )

    def download_purchase_order(self,obj):
        return format_html("<a href= '%s' >Download PO</a>"%(reverse('admin:download_purchase_order', args=[obj.pk])))
    download_purchase_order.short_description = 'Download Purchase Order'

    def get_list_display(self, request):

<<<<<<< HEAD
            data = {}
            data['link_to_po'] = self.download_purchase_order()
            data['shop_id'] = self.gf_shipping_address.shop_name.id
            activity_type = "PO_APPROVED"
            from notification_center.utils import SendNotification
            SendNotification(activity_type=activity_type, data=data).send_to_a_group()    

            return HttpResponseRedirect("/admin/gram_to_brand/cart/")
        elif "_disapprove" in request.POST:
            if request.POST.get('message'):
                get_po_msg, _ = Po_Message.objects.get_or_create(message=request.POST.get('message'))
                obj.po_message = get_po_msg
            obj.is_approve = False
            obj.po_status = obj.UNAPPROVED
            obj.created_by = request.user
            obj.last_modified_by = request.user
            obj.save()
=======
        def po_edit_link(obj):
            if request.user.is_superuser:
                return format_html("<a href= '/admin/gram_to_brand/cart/%s/change/' >%s</a>" % (obj.pk, obj.po_no))
            if request.user.has_perm('gram_to_brand.can_create_po') and obj.po_status == obj.APPROVAL_AWAITED:
                return format_html("%s" %obj.po_no)
            return format_html("<a href= '/admin/gram_to_brand/cart/%s/change/' >%s</a>" % (obj.pk,obj.po_no))
        po_edit_link.short_description = 'Po No'
>>>>>>> dev

        return [po_edit_link,'brand','supplier_state','supplier_name', 'po_creation_date','po_validity_date','po_raised_by','po_status', 'download_purchase_order']

<<<<<<< HEAD
            # PO Number, Date, HTML of PO, link to PO should be mailed
            data = {}
            data['link_to_po'] = self.download_purchase_order()
            data['shop_id'] = self.gf_shipping_address.shop_name.id
            activity_type = "PO_EDITED"
            from notification_center.utils import SendNotification
            SendNotification(activity_type=activity_type, data=data).send_to_a_group()    

        return super().response_change(request, obj)
=======
    def save_formset(self, request, form, formset, change):
        obj = form.instance
        flag = False
        get_po_msg = Po_Message.objects.create(message=request.POST.get('message'),
                                               created_by=request.user) if request.POST.get('message') else None
>>>>>>> dev

        if "_approve" in request.POST:
            obj.po_status = obj.FINANCE_APPROVED
            flag = True
        elif "_disapprove" in request.POST:
            obj.po_status = obj.DISAPPROVED
            flag = True
        elif "_approval_await" in request.POST:
            obj.po_status = obj.APPROVAL_AWAITED
            flag = True
        elif "_close" in request.POST:
            obj.po_status = obj.PARTIAL_DELIVERED_CLOSE
            flag = True
        else:
            obj.po_status = obj.OPEN
        obj.po_message = get_po_msg
        obj.po_raised_by = request.user
        obj.last_modified_by = request.user
        obj.save()
        formset.save()
        if flag:
            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=ContentType.objects.get_for_model(obj).pk,
                object_id=obj.pk,
                action_flag=ADDITION,
                object_repr='',
                change_message=SUCCESS_MESSAGES['CHANGED_STATUS'] % obj.get_po_status_display(),
            )
            return HttpResponseRedirect("/admin/gram_to_brand/cart/")

            data = {}
            data['link_to_po'] = self.download_purchase_order()
            data['shop_id'] = self.gf_shipping_address.shop_name.id

            user_id = instance.order_id.ordered_by.id
            activity_type = "PO_CREATED"
            from notification_center.utils import SendNotification
            SendNotification(activity_type=activity_type, data=data).send_to_a_group()    


    class Media:
            pass

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

    """
        TextArea Rows and columns can set here
    """
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 33})},
    }

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return 'po_status',
        elif request.user.has_perm('gram_to_brand.can_approve_and_disapprove'):
            return 'brand', 'supplier_state','supplier_name', 'gf_shipping_address','gf_billing_address', 'po_validity_date', 'payment_term','delivery_term','po_status',
        return 'po_status',

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if request.user.is_superuser:
            defaults['form'] = POGenerationForm
        elif request.user.has_perm('gram_to_brand.can_approve_and_disapprove'):
            defaults['form'] = POGenerationAccountForm
        else:
            defaults['form'] = POGenerationForm
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

class GRNOrderForm(forms.ModelForm):
    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        widget=autocomplete.ModelSelect2(url='order-autocomplete',)
    )

    class Meta:
        model = GRNOrder
        fields = ('order', 'invoice_no',)

class DocumentAdmin(admin.StackedInline):
    model = Document
    fields = ('document_number', 'document_image')
    extra = 0

class GRNOrderProductMappingAdmin(admin.TabularInline):
    model = GRNOrderProductMapping
    formset = GRNOrderProductFormset
    form = GRNOrderProductForm
    fields = ('product', 'product_mrp', 'po_product_quantity','po_product_price','already_grned_product','product_invoice_price','manufacture_date',
              'expiry_date','best_before_year','best_before_month','product_invoice_qty','delivered_qty','returned_qty')
    exclude = ('last_modified_by','available_qty',)
    extra = 0
    #readonly_fields = ('po_product_quantity','po_product_price','already_grned_product',)
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('product','product_mrp','po_product_quantity','po_product_price','already_grned_product',)
        return self.readonly_fields

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(GRNOrderProductMappingAdmin, self).get_formset(request, obj, **kwargs)
        cart_id = request.GET.get('cart')
        if cart_id:
            formset.order = Cart.objects.get(pk=int(cart_id))
        return formset

class BrandNoteAdmin(admin.ModelAdmin):
    model = BrandNote
    list_display = ('brand_note_id','grn_order',  'amount')
    exclude = ('brand_note_id','last_modified_by',)

class OrderItemAdmin(admin.ModelAdmin):
    list_filter = [OrderSearch , QuantitySearch, PORaisedBy ,('order__ordered_cart__po_creation_date', DateRangeFilter)]
    list_display = ('order','ordered_product','ordered_qty','total_delivered_qty','total_damaged_qty','po_creation_date','item_status',)

    def po_creation_date(self, obj):
        return "%s" % (obj.order.ordered_cart.po_creation_date)

    po_creation_date.short_description = 'Po Creation Date'


class GRNOrderAdmin(admin.ModelAdmin):
    inlines = [DocumentAdmin, GRNOrderProductMappingAdmin]
    autocomplete_fields = ('order',)
    exclude = ('order_item','grn_id','last_modified_by',)
    #list_display_links = None
    list_display = ('grn_id','order','invoice_no','grn_date','brand', 'supplier_state', 'supplier_name','po_status', 'po_created_by','download_debit_note')
    list_filter = [OrderSearch, InvoiceNoSearch, GRNSearch, ('created_at', DateRangeFilter),('grn_order_grn_order_product__expiry_date', DateRangeFilter)]
    form = GRNOrderForm
    #fields = ('order','invoice_no','brand_invoice','e_way_bill_no','e_way_bill_document', 'invoice_date', 'invoice_amount')
    fields = ('order','invoice_no','invoice_date', 'invoice_amount')
    change_form_template = 'admin/gram_to_brand/grn_order/change_form.html'

    def po_created_by(self,obj):
        return obj.order.ordered_cart.po_raised_by
    po_created_by.short_description = 'PO Creadted By'

    def brand(self,obj):
        return obj.order.ordered_cart.brand
    brand.short_description = 'Brand'

    def supplier_state(self,obj):
        return obj.order.ordered_cart.supplier_state
    supplier_state.short_description = 'Supplier State'

    def supplier_name(self,obj):
        return obj.order.ordered_cart.supplier_name
    supplier_name.short_description = 'Supplier Name'

    def po_status(self,obj):
        return obj.order.ordered_cart.get_po_status_display()
    po_status.short_description = 'Po Status'


    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('order', )
        return self.readonly_fields

    def get_queryset(self, request):
        qs = super(GRNOrderAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__ordered_cart__gf_shipping_address__shop_name__related_users=request.user) |
            Q(order__ordered_cart__gf_shipping_address__shop_name__shop_owner=request.user)
        )

    def download_debit_note(self,obj):
        if obj.grn_order_brand_note.count()>0 and obj.grn_order_brand_note.filter(status=True):
            return format_html("<a href= '%s' >Download Debit Note</a>"%(reverse('download_debit_note', args=[obj.pk])))

    download_debit_note.short_description = 'Download Debit Note'
    change_list_template = 'admin/gram_to_brand/order/change_list.html'

    def save_related(self, request, form, formsets, change):
        flag = 'DLVR'
        super(GRNOrderAdmin, self).save_related(request, form, formsets, change)
        obj = form.instance
        obj.order.ordered_cart.cart_list.values('cart_product', 'no_of_pieces')
        grn_list_map = {int(i['product']): (i['delivered_qty_sum'],i['returned_qty_sum']) for i in GRNOrderProductMapping.objects.filter(grn_order__order=obj.order).values('product')
            .annotate(delivered_qty_sum=Sum(F('delivered_qty')))
            .annotate(returned_qty_sum=Sum(F('returned_qty')))}
        returned_qty_totalsum = GRNOrderProductMapping.objects.filter(grn_order__order=obj.order).aggregate(returned_qty_totalsum=Sum('returned_qty'))['returned_qty_totalsum']
        for product_price_map in obj.order.ordered_cart.cart_list.values('cart_product', 'no_of_pieces'):
            if returned_qty_totalsum >0:
                flag = 'PDLC'
                if grn_list_map[product_price_map['cart_product']][0] == 0 and grn_list_map[product_price_map['cart_product']][1] >= 0:
                    flag = 'PARR'
                elif grn_list_map[product_price_map['cart_product']][0] + grn_list_map[product_price_map['cart_product']][1] != product_price_map['no_of_pieces']:
                    flag = 'PDLV'
                    break
            elif grn_list_map[product_price_map['cart_product']][0] != product_price_map['no_of_pieces']:
                flag = 'PDLV'
                break
        obj.order.ordered_cart.po_status = flag
        obj.order.ordered_cart.save()

class OrderAdmin(admin.ModelAdmin):
    search_fields = ['order_no',]
    list_display = ('order_no', 'brand', 'supplier_state', 'supplier_name', 'created_at','po_status', 'created_by', 'add_grn_link')
    form= OrderForm

    def created_by(self,obj):
        return obj.ordered_cart.po_raised_by
    created_by.short_description = 'Creadted By'

    def brand(self,obj):
        return obj.ordered_cart.brand
    brand.short_description = 'Brand'

    def supplier_state(self,obj):
        return obj.ordered_cart.supplier_state
    supplier_state.short_description = 'Supplier State'

    def supplier_name(self,obj):
        return obj.ordered_cart.supplier_name
    supplier_name.short_description = 'Supplier Name'

    def po_status(self,obj):
        return obj.ordered_cart.get_po_status_display()
    po_status.short_description = 'Po Status'

    def add_grn_link(self, obj):
        if obj.ordered_cart.po_status in [obj.ordered_cart.FINANCE_APPROVED,obj.ordered_cart.PARTIAL_DELIVERED,obj.ordered_cart.PARTIAL_RETURN] :
            return format_html("<a href = '/admin/gram_to_brand/grnorder/add/?order=%s&cart=%s' class ='addlink' > Add GRN</a>"% (obj.id, obj.ordered_cart.id))

    add_grn_link.short_description = 'Add GRN'

    change_list_template = 'admin/gram_to_brand/order/change_list.html'


class PickListItemAdmin(admin.TabularInline):
    model = PickListItems

class PickListAdmin(admin.ModelAdmin):
    inlines = [PickListItemAdmin]

admin.site.register(PickList,PickListAdmin)

class OrderedProductReservedAdmin(admin.ModelAdmin):
    list_display = ('order_product_reserved','cart','product','reserved_qty','order_reserve_end_time','created_at','reserve_status')


admin.site.register(Cart,CartAdmin)
admin.site.register(OrderedProductReserved,OrderedProductReservedAdmin)
admin.site.register(Order,OrderAdmin)
admin.site.register(GRNOrder,GRNOrderAdmin)
#admin.site.register(BrandNote,BrandNoteAdmin)
