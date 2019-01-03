from django.contrib import admin
from .models import (Order,Cart,CartProductMapping,GRNOrder,GRNOrderProductMapping,OrderItem,BrandNote,PickList,PickListItems,
                     OrderedProductReserved,Po_Message)
from products.models import Product
from django import forms
from django.db.models import Sum
from django.utils.html import format_html
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from dal import autocomplete
from retailer_backend.admin import InputFilter
from django.db.models import Q
from django.utils.html import format_html
from django.urls import reverse

from brand.models import Brand
from addresses.models import State,Address
from brand.models import Vendor
from shops.models import Shop
from daterange_filter.filter import DateRangeFilter
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from admin_auto_filters.filters import AutocompleteFilter
from gram_to_brand.forms import OrderForm
from .forms import POGenerationForm
from django.http import HttpResponse, HttpResponseRedirect

class BrandFilter(AutocompleteFilter):
    title = 'Brand' # display title
    field_name = 'brand' # name of the foreign key field


class SupplierStateFilter(AutocompleteFilter):
    title = 'State' # display title
    field_name = 'supplier_state' # name of the foreign key field


class SupplierFilter(AutocompleteFilter):
    title = 'Supplier' # display title
    field_name = 'supplier_name' # name of the foreign key field


class OrderSearch(InputFilter):
    parameter_name = 'order'
    title = 'PO No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order = self.value()
            if order is None:
                return
            return queryset.filter(
                Q(order__order_no__icontains=order)
            )

class QuantitySearch(InputFilter):
    parameter_name = 'qty'
    title = 'Ordered Qty'

    def queryset(self, request, queryset):
        if self.value() is not None:
            qty = self.value()
            if qty is None:
                return
            return queryset.filter(
                Q(ordered_qty__icontains=qty)
            )

class InvoiceNoSearch(InputFilter):
    parameter_name = 'invoice_no'
    title = 'Invoice No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            invoice_no = self.value()
            if invoice_no is None:
                return
            return queryset.filter(
                Q(invoice_no__icontains=invoice_no)
            )

class GRNSearch(InputFilter):
    parameter_name = 'grn_id'
    title = 'GRN No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            grn_id = self.value()
            if grn_id is None:
                return
            return queryset.filter(
                Q(grn_id__icontains=grn_id)
            )

class POAmountSearch(InputFilter):
    parameter_name = 'po_amount'
    title = 'PO Amount'

    def queryset(self, request, queryset):
        if self.value() is not None:
            po_amount = self.value()
            if po_amount is None:
                return
            return queryset.filter(
                Q(po_amount=po_amount)
            )

class PORaisedBy(InputFilter):
    parameter_name = 'po_raised_by'
    title = 'PO Raised By'

    def queryset(self, request, queryset):
        if self.value() is not None:
            po_raised_by = self.value()
            if po_raised_by is None:
                return
            # return queryset.filter(
            #     Q(po_raised_by=po_raised_by)
            # )
            any_name = Q()
            for name in po_raised_by.split():
                any_name &= (
                    Q(po_raised_by__first_name__icontains=name) |
                    Q(po_raised_by__last_name__icontains=name)
                )
            return queryset.filter(any_name)

class CartProductMappingForm(forms.ModelForm):

    cart_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='vendor-product-autocomplete', forward=('supplier_name',))
    )

    class Meta:
        model = CartProductMapping
        fields = ('cart_product','case_size', 'number_of_cases','scheme','price','total_price',)
        search_fields=('cart_product',)
        exclude = ('qty',)



class CartProductMappingFormset(forms.models.BaseInlineFormSet):

    def clean(self):
        count = 0
        for form in self.forms:
            try:
                if form.cleaned_data:
                    count += 1
            except AttributeError:
                # annoyingly, if a subform is invalid Django explicity raises
                # an AttributeError for cleaned_data
                pass
        if count < 1:
            raise forms.ValidationError('You must have at least one product')


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    #readonly_fields = ('get_edit_link',)
    autocomplete_fields = ('cart_product',)
    search_fields =('cart_product',)
    #formset = CartProductMappingFormset
    form = CartProductMappingForm

class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'shop', 'po_status','last_modified_by')
    autocomplete_fields = ('brand',)
    list_display = ('po_no','brand','supplier_state','supplier_name', 'po_creation_date','po_validity_date','po_amount','is_approve','po_raised_by','po_status', 'download_purchase_order')
    list_filter = [BrandFilter,SupplierStateFilter ,SupplierFilter,('po_creation_date', DateRangeFilter),('po_validity_date', DateRangeFilter),POAmountSearch,PORaisedBy]
    form = POGenerationForm
    def download_purchase_order(self,obj):
        if obj.is_approve:
            return format_html("<a href= '%s' >Download PO</a>"%(reverse('download_purchase_order', args=[obj.pk])))

    download_purchase_order.short_description = 'Download Purchase Order'

    # def save_formset(self, request, form, formset, change):
    #     import datetime
    #     today = datetime.date.today()
    #     instances = formset.save(commit=False)
    #     flag = 0
    #     new_order = ''
    #     for instance in instances:
    #
    #         instance.last_modified_by = request.user
    #         instance.save()
    #         #print(instance.cart)
    #         #Save Order
    #         #order,_ = Order.objects.get_or_create(ordered_cart=instance.cart)
    #         order,_ = Order.objects.get_or_create(ordered_cart=instance.cart,order_no=instance.cart.po_no)
    #         order.ordered_by=request.user
    #         order.order_status='ordered_to_brand'
    #         order.last_modified_by=request.user
    #         order.save()
    #
    #         #Save OrderItem
    #         if OrderItem.objects.filter(order=order,ordered_product=instance.cart_product).exists():
    #             OrderItem.objects.filter(order=order,ordered_product=instance.cart_product).delete()
    #
    #         order_item = OrderItem()
    #         order_item.ordered_product = instance.cart_product
    #         order_item.ordered_qty = instance.number_of_cases * instance.case_size
    #         order_item.ordered_price = instance.price
    #
    #         order_item.order = order
    #         order_item.last_modified_by = request.user
    #         order_item.save()
    #
    #         #instance.order_brand.ordered_by = request.user
    #         #instance.order_brand.order_status = 'ordered_to_brand'
    #         #nstance.order_brand.brand_order_id = 'BRAND/ORDER/' + str(instance.order_brand.id)
    #         #new_order = instance.order_brand
    #
    #         #Order.objects.get_or_create('ordered_cart'=instance.cart_list)
    #         #instance.order_brand.save()
    #         #instance.cart_id = 'BRAND-' + "{%Y%m%d}".format(today) + "-" + instance.id
    #         #instance.shop = Shop.objects.get(name='Gramfactory')
    #
    #     # if request.user.groups.filter(name='grn_brand_to_gram_group').exists():
    #     #     if new_order and CartToBrand.objects.filter(order_brand=new_order):
    #     #         new_order.order_status = 'partially_delivered'
    #     #     elif new_order:
    #     #         new_order.order_status = 'delivered'
    #     #     new_order.save()
    #     formset.save_m2m()

    def response_change(self, request, obj):
        if "_approve" in request.POST:
            if request.POST.get('message'):
                get_po_msg,_ = Po_Message.objects.get_or_create(message=request.POST.get('message'))
                obj.po_message = get_po_msg
            obj.is_approve = True
            obj.created_by = request.user
            obj.save()
            return HttpResponseRedirect("/admin/gram_to_brand/cart/")
        elif "_disapprove" in request.POST:
            if request.POST.get('message'):
                get_po_msg, _ = Po_Message.objects.get_or_create(message=request.POST.get('message'))
                obj.po_message = get_po_msg
            obj.is_approve = False
            obj.created_by = request.user
            obj.save()
            return HttpResponseRedirect("/admin/gram_to_brand/cart/")
        else:
            obj.is_approve = ''
            obj.save()
        return super().response_change(request, obj)

    class Media:
            pass


admin.site.register(Cart,CartAdmin)


# testing st

from django.utils.functional import curry


class GRNOrderForm(forms.ModelForm):
    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        widget=autocomplete.ModelSelect2(url='order-autocomplete',)
    )

    class Meta:
        model = GRNOrder
        fields = ('order','invoice_no')

    # def __init__(self, *args, **kwargs):
    #     #print("mukesh")
    #     self.initial = [
    #         {'label': 'first name'},
    #         {'label': 'last name'},
    #         {'label': 'job', }
    #     ]
    #     super(GRNOrderForm, self).__init__(*args, **kwargs)

class GRNOrderProductForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='product-autocomplete',forward=('order',))
     )
    class Meta:
        model = GRNOrderProductMapping
        fields = ('product','po_product_quantity','po_product_price','already_grned_product','product_invoice_price','manufacture_date','expiry_date','product_invoice_qty','available_qty','delivered_qty','returned_qty')
        readonly_fields = ('product')
        autocomplete_fields = ('product',)

    class Media:
        pass
        #css = {'all': ('pretty.css',)}
        js = ('/static/admin/js/grn_form.js',)

    # def __init__(self, exp = None, *args, **kwargs):
    #     super(GRNOrderProductForm, self).__init__(*args, **kwargs)
    #     #order_id= self.request.GET.get('order_id')
    #     cart_products = CartProductMapping.objects.filter(cart__id='17').values_list('cart_product').order_by('product_order_item')
    #     products = Product.objects.filter(pk__in=cart_products)
    #     self.fields["product"].queryset = products


    # data = {
    #     'subject': 'hello',
    #     'sender': 'foo@example.com',
    #     'cc_myself': True
    # }

# class DetailsFormset(forms.models.BaseInlineFormSet):
#     def __init__(self, *args, **kwargs):
#         self.initial = [
#             {'label': 'first name'},
#             {'label': 'last name'},
#             {'label': 'job', }
#         ]
#         super(DetailsFormset, self).__init__(*args, **kwargs)

# class DetailsInline(admin.TabularInline):
#     model = Details
#     formset = DetailsFormset
#     extra = 3
#
#     def get_formset(self, request, obj=None, **kwargs):
#         initial = []
#         if request.method == "GET":
#             initial.append({
#                 'label': 'first name',
#             })
#         formset = super(DetailsInline, self).get_formset(request, obj, **kwargs)
#         formset.__init__ = curry(formset.__init__, initial=initial)
#         return formset

from django.contrib.admin.widgets import RelatedFieldWidgetWrapper

#from .widgets import DataAttributesSelect

# class MyModelAdminForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(MyModelAdminForm, self).__init__(*args, **kwargs)
#
#         data = {'data-foo': dict(MyModelChoice.objects.values_list('id', 'foo'))}
#         data['data-foo'][''] = ''  # empty option
#
#         self.fields['myselectfield'].widget = RelatedFieldWidgetWrapper(
#             DataAttributesSelect(
#                 choices=self.fields['myselectfield'].choices,
#                 data=data
#             ),
#             self.fields['myselectfield'].widget.rel,
#             self.fields['myselectfield'].widget.admin_site,
#             self.fields['myselectfield'].widget.can_add_related,
#             self.fields['myselectfield'].widget.can_change_related,
#             self.fields['myselectfield'].widget.can_delete_related,
#         )


# class MyModelAdminForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(MyModelAdminForm, self).__init__(*args, **kwargs)
#         data = {'data-cart_product': {'': ''}}  # empty option
#         for f in Product.objects.all():
#             data['cart_product'][f.id] = f.id
#
#         self.fields['cart_product'].widget = DataAttributesSelect(
#             choices=[('', '-----')] + [(f.id, str(f)) for f in Product.objects.all()],  # noqa
#             data=data
#         )

# testing end

def get_product(self,*args,**kwargs):
    qs = Product.objects.all()
    order_id = self.forwarded.get('order', None)
    if order_id:
        order = Order.objects.get(id=order_id)
        cp_products = CartProductMapping.objects.filter(cart=order.ordered_cart).values('cart_product')
        qs = qs.filter(id__in=[cp_products])

    return qs

class GRNOrderProductMappingAdmin(admin.TabularInline):
    model = GRNOrderProductMapping
    form = GRNOrderProductForm

    extra= 10
    exclude = ('last_modified_by','available_qty',)
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('po_product_quantity','po_product_price','already_grned_product',)
        return self.readonly_fields

    #readonly_fields= ('po_product_price', 'po_product_quantity', 'already_grned_product')

    # def get_formset(self, request, obj=None, **kwargs):
    #     initial = []
    #     print(request.method)
    #     # if request.method == "GET":
    #     #     initial.append({
    #     #         'label': 'product',
    #     #     })
    #     ArticleFormSet = formset_factory(GRNOrderProductForm, extra=1)
    #     formset = ArticleFormSet(initial=[{'product_invoice_price': '10'}])


    #     #self.initial = [{'product_invoice_price':1},{'product_invoice_price':1,}]
    #     #self.fields['product'] = Product.objects.get(id=4)
    #     #formset = super(GRNOrderProductMappingAdmin, self).get_formset(request, obj, **kwargs)
    #     #formset.__init__ = curry(formset.__init__, initial=initial)
    #     return formset

    # def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
    #     order_id = request.GET.get('odr')
    #
    #     if db_field.name == 'product':
    #         kwargs['queryset'] = Product.objects.filter(product_order_item__order__id=order_id)
    #
    #     return super(GRNOrderProductMappingAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class BrandNoteAdmin(admin.ModelAdmin):
    model = BrandNote
    list_display = ('brand_note_id','order','grn_order', 'note_type', 'amount')
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
    list_display = ('grn_id','order','invoice_no','grn_date','edit_grn_link')
    list_filter = [ OrderSearch, InvoiceNoSearch, GRNSearch, ('created_at', DateRangeFilter),]
    form = GRNOrderForm

    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('order', )
        return self.readonly_fields


    def edit_grn_link(self, obj):
        #return format_html("<ul class ='object-tools'><li><a href = '/admin/gram_to_brand/grnorder/add/?brand=%s' class ='addlink' > Add order</a></li></ul>"% (obj.id))
        return format_html("<a href = '/admin/gram_to_brand/grnorder/%s/change/?order=%s&odr=%s' class ='addlink' > Edit GRN</a>"% (obj.id,obj.id,obj.id))

    edit_grn_link.short_description = 'Edit GRN'


    # def __init__(self, *args, **kwargs):
    #     super(GRNOrderAdmin, self).__init__(*args, **kwargs)
    #     self.list_display_links = None


    # def __init__(self, *args, **kwargs):
    #     super(GRNOrderAdmin, self).__init__(*args, **kwargs)
    #     self.list_display_links = None


    # def get_form(self, request, obj=None, **kwargs):
    #     #request.current_object = obj
    #     return super(GRNOrderAdmin, self).get_form(request, obj, **kwargs)

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        order_id = 0

        print(instances)
        #print(instances.count())

        for instance in instances:
            #GRNOrderProductMapping
            #Save OrderItem
            if OrderItem.objects.filter(order=instance.grn_order.order,ordered_product=instance.product).exists():
                order_item = OrderItem.objects.get(order=instance.grn_order.order, ordered_product=instance.product)
                if GRNOrderProductMapping.objects.filter(grn_order__order=instance.grn_order.order,product=instance.product).exists():
                    product_grouped_info = GRNOrderProductMapping.objects.filter(grn_order__order=instance.grn_order.order,product=instance.product)\
                        .aggregate(total_delivered_qty=Sum('delivered_qty'),total_returned_qty=Sum('returned_qty'),total_damaged_qty=Sum('damaged_qty'))

                    order_item.total_delivered_qty = product_grouped_info['total_delivered_qty']
                    order_item.total_returned_qty = product_grouped_info['total_returned_qty']
                    order_item.total_damaged_qty = product_grouped_info['total_damaged_qty']
                    if product_grouped_info['total_delivered_qty'] == order_item.ordered_qty:
                        order_item.item_status = 'delivered'
                    else:
                        order_item.item_status = 'partially_delivered'
                else:

                    order_item.total_delivered_qty = instance.delivered_qty
                    order_item.total_returned_qty = instance.returned_qty
                    order_item.total_damaged_qty = instance.damaged_qty
                    if instance.delivered_qty == order_item.ordered_qty:
                        order_item.item_status = 'delivered'
                    else:
                        order_item.item_status = 'partially_delivered'

                order_item.save()
                instance.available_qty = int(instance.delivered_qty)
                instance.grn_order.order.order_status='partially_delivered'
                instance.grn_order.order.save()
                order_id = instance.grn_order.order.id
                instance.save()
            #Update Order
        if order_id!= 0 and OrderItem.objects.filter(order=order_id).exists():
            order = Order.objects.get(id=order_id)
            order_item = OrderItem.objects.filter(order=order_id)
            order.order_status = 'partially_delivered' if order_item.filter(item_status='partially_delivered').count()>0 else 'delivered'
            order.save()

        formset.save_m2m()


class OrderAdmin(admin.ModelAdmin):
    search_fields = ['order_no',]
    list_display = ('order_no','order_status','ordered_by','created_at','add_grn_link')
    form= OrderForm

    def add_grn_link(self, obj):
        return format_html("<a href = '/admin/gram_to_brand/grnorder/add/?order=%s&odr=%s' class ='addlink' > Add GRN</a>"% (obj.id,obj.id))

    add_grn_link.short_description = 'Do GRN'

admin.site.register(Order,OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(GRNOrder,GRNOrderAdmin)
admin.site.register(BrandNote,BrandNoteAdmin)

class PickListItemAdmin(admin.TabularInline):
    model = PickListItems

class PickListAdmin(admin.ModelAdmin):
    inlines = [PickListItemAdmin]

admin.site.register(PickList,PickListAdmin)

class OrderedProductReservedAdmin(admin.ModelAdmin):
    list_display = ('order_product_reserved','product','cart','reserved_qty','order_reserve_end_time','created_at')

admin.site.register(OrderedProductReserved,OrderedProductReservedAdmin)

from django.utils.functional import curry
from django.forms import formset_factory
#from django import OrderShipmentFrom
from django.forms import BaseFormSet
from django.forms.models import BaseModelFormSet ,BaseInlineFormSet
#from .forms import OrderShipmentFrom
