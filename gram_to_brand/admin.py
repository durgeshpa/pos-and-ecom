from django.contrib import admin
from .models import (Order,Cart,CartProductMapping,GRNOrder,GRNOrderProductMapping,BrandNote,PickList,PickListItems,
                     OrderedProductReserved,Po_Message)
from products.models import Product
from django import forms
from django.db.models import Sum
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
from gram_to_brand.forms import (OrderForm, CartProductMappingForm, GRNOrderForm, GRNOrderProductForm, GRNOrderProductFormset)
from .forms import POGenerationForm
from django.http import HttpResponse, HttpResponseRedirect
from retailer_backend.filters import ( BrandFilter, SupplierStateFilter,SupplierFilter, OrderSearch, QuantitySearch, InvoiceNoSearch,
                                       GRNSearch, POAmountSearch, PORaisedBy)

from django.db.models import Q


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    #readonly_fields = ('get_edit_link',)
    autocomplete_fields = ('cart_product',)
    search_fields =('cart_product',)
    #formset = CartProductMappingFormset
    form = CartProductMappingForm


class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'po_status','last_modified_by')
    autocomplete_fields = ('brand',)
    list_display = ('po_no','brand','supplier_state','supplier_name', 'po_creation_date','po_validity_date','is_approve','po_raised_by','po_status', 'download_purchase_order')
    list_filter = [BrandFilter,SupplierStateFilter ,SupplierFilter,('po_creation_date', DateRangeFilter),('po_validity_date', DateRangeFilter),POAmountSearch,PORaisedBy]
    form = POGenerationForm

    def get_queryset(self, request):
        qs = super(CartAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.has_perm('gram_to_brand.can_approve_and_disapprove'):
            return qs
        return qs.filter(
            Q(gf_shipping_address__shop_name__related_users=request.user) |
            Q(gf_shipping_address__shop_name__shop_owner=request.user)
                )

    def download_purchase_order(self,obj):
        if obj.is_approve:
            return format_html("<a href= '%s' >Download PO</a>"%(reverse('download_purchase_order', args=[obj.pk])))

    download_purchase_order.short_description = 'Download Purchase Order'

    def response_change(self, request, obj):
        if "_approve" in request.POST:
            if request.POST.get('message'):
                get_po_msg,_ = Po_Message.objects.get_or_create(message=request.POST.get('message'))
                obj.po_message = get_po_msg
            obj.is_approve = True
            obj.po_status = 'finance_approved'
            obj.created_by = request.user
            obj.last_modified_by = request.user
            obj.save()

            return HttpResponseRedirect("/admin/gram_to_brand/cart/")
        elif "_disapprove" in request.POST:
            if request.POST.get('message'):
                get_po_msg, _ = Po_Message.objects.get_or_create(message=request.POST.get('message'))
                obj.po_message = get_po_msg
            obj.is_approve = False
            obj.po_status = 'finance_not_approved'
            obj.created_by = request.user
            obj.last_modified_by = request.user
            obj.save()

            return HttpResponseRedirect("/admin/gram_to_brand/cart/")
        else:
            obj.is_approve = ''
            obj.po_status = 'waiting_for_finance_approval'
            obj.po_raised_by= request.user
            obj.last_modified_by= request.user
            obj.save()

        return super().response_change(request, obj)

    def save_model(self, request, obj, form, change):
        if change==False:
            obj.is_approve = ''
            obj.po_status = 'waiting_for_finance_approval'
            obj.po_raised_by = request.user
            obj.last_modified_by = request.user
            obj.save()

    class Media:
            pass



admin.site.register(Cart,CartAdmin)


from django.utils.functional import curry


class GRNOrderForm(forms.ModelForm):
    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        widget=autocomplete.ModelSelect2(url='order-autocomplete',)
    )

    class Meta:
        model = GRNOrder
        fields = ('order', 'invoice_no')


class GRNOrderProductMappingAdmin(admin.TabularInline):
    model = GRNOrderProductMapping
    formset = GRNOrderProductFormset
    form = GRNOrderProductForm
    exclude = ('last_modified_by','available_qty',)
    extra = 0
    readonly_fields = ('po_product_quantity','po_product_price','already_grned_product',)
    # def get_readonly_fields(self, request, obj=None):
    #     if obj: # editing an existing object
    #         return self.readonly_fields + ('po_product_quantity','po_product_price','already_grned_product',)
    #     return self.readonly_fields

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
    inlines = [GRNOrderProductMappingAdmin]
    autocomplete_fields = ('order',)
    exclude = ('order_item','grn_id','last_modified_by',)
    #list_display_links = None
    list_display = ('grn_id','order','invoice_no','grn_date','download_debit_note')
    list_filter = [ OrderSearch, InvoiceNoSearch, GRNSearch, ('created_at', DateRangeFilter),]
    form = GRNOrderForm
    fields = ('order','invoice_no')

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
            Q(order__ordered_cart__gf_shipping_address__shop_name__shop_owner
              =request.user)
        )


    def download_debit_note(self,obj):
        if obj.grn_order_brand_note.count()>0 and obj.grn_order_brand_note.filter(status=True):
            return format_html("<a href= '%s' >Download Debit Note</a>"%(reverse('download_debit_note', args=[obj.pk])))

    download_debit_note.short_description = 'Download Debit Note'


class OrderAdmin(admin.ModelAdmin):
    search_fields = ['order_no',]
    list_display = ('order_no','created_at','add_grn_link')
    form= OrderForm

    def add_grn_link(self, obj):
        return format_html("<a href = '/admin/gram_to_brand/grnorder/add/?order=%s&cart=%s' class ='addlink' > Add GRN</a>"% (obj.id, obj.ordered_cart.id))

    add_grn_link.short_description = 'Do GRN'


class PickListItemAdmin(admin.TabularInline):
    model = PickListItems

class PickListAdmin(admin.ModelAdmin):
    inlines = [PickListItemAdmin]

admin.site.register(PickList,PickListAdmin)

class OrderedProductReservedAdmin(admin.ModelAdmin):
    list_display = ('order_product_reserved','cart','product','reserved_qty','order_reserve_end_time','created_at','reserve_status')


admin.site.register(OrderedProductReserved,OrderedProductReservedAdmin)
admin.site.register(Order,OrderAdmin)
admin.site.register(GRNOrder,GRNOrderAdmin)
#admin.site.register(BrandNote,BrandNoteAdmin)
