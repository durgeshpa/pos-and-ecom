from django.contrib import admin
from .models import Order,Cart,CartProductMapping,GRNOrder,GRNOrderProductMapping,OrderItem,BrandNote
from products.models import Product
from django import forms
from django.db.models import Sum
from django.utils.html import format_html
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from dal import autocomplete
from retailer_backend.admin import InputFilter
from django.db.models import Q

from brand.models import Brand
from addresses.models import State,Address
from shops.models import Shop
from daterange_filter.filter import DateRangeFilter

class BrandSearch(InputFilter):
    parameter_name = 'brand'
    #title = _('Brand')
    title = 'Brand'

    def queryset(self, request, queryset):
        if self.value() is not None:
            brand = self.value()
            if brand is None:
                return
            return queryset.filter(
                Q(brand__brand_name__icontains=brand)
            )

class StateSearch(InputFilter):
    parameter_name = 'state'
    title = 'State'

    def queryset(self, request, queryset):
        if self.value() is not None:
            state = self.value()
            if state is None:
                return
            return queryset.filter(
                Q(state__state_name__icontains=state)
            )

class SupplierSearch(InputFilter):
    parameter_name = 'supplier'
    title = 'Supplier'

    def queryset(self, request, queryset):
        if self.value() is not None:
            supplier = self.value()
            if supplier is None:
                return
            return queryset.filter(
                Q(supplier__shop_name__icontains=supplier)
            )

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
    title = 'Qty'

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


# class UserFilter(InputFilter):
#     parameter_name = 'user'
#     title = _('User')
#     def queryset(self, request, queryset):
#         term = self.value()
#         if term is None:
#             return
#         any_name = Q()
#         for bit in term.split():
#             any_name &= (
#                 Q(user__first_name__icontains=bit) |
#                 Q(user__last_name__icontains=bit)
#             )
#         return queryset.filter(any_name)


class POGenerationForm(forms.ModelForm):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        widget=autocomplete.ModelSelect2(url='brand-autocomplete',)
    )
    supplier_state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        widget=autocomplete.ModelSelect2(url='state-autocomplete',)
    )
    supplier_name = forms.ModelChoiceField(
        queryset=Shop.objects.all(),
        widget=autocomplete.ModelSelect2(url='supplier-autocomplete',forward=('state','brand'))
    )
    gf_shipping_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(url='shipping-address-autocomplete', forward=('state',))
    )
    gf_billing_address = forms.ModelChoiceField(
        queryset=Address.objects.filter(shop_name__shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(url='billing-address-autocomplete', forward=('state',))
    )

    # country = forms.ModelChoiceField(
    #     queryset=Country.objects.all(),
    #     widget=autocomplete.ModelSelect2(url='country-autocomplete'))
    # city = forms.ModelChoiceField(
    #     queryset=City.objects.all(),
    #     widget=autocomplete.ModelSelect2(
    #
    #     # attrs={
    #     #     'data-placeholder': 'Autocomplete ...',
    #     #     'data-minimum-input-length': 3,
    #     # },
    #     url='city-autocomplete',
    #     forward=('country',)))

    class Media:
        pass
        #css = {'all': ('pretty.css',)}
        #js = ('/static/assets/js/custom.js',)

    class Meta:
        model = Cart
        fields = ('brand','supplier_state','supplier_name','gf_shipping_address','gf_billing_address','po_validity_date','payment_term','delivery_term')

class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    #readonly_fields = ('get_edit_link',)
    autocomplete_fields = ('cart_product',)

class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'shop', 'po_status','last_modified_by')
    autocomplete_fields = ('brand',)
    list_display = ('po_no','brand','state','supplier_name', 'po_creation_date','po_validity_date','po_amount','po_raised_by','po_status')
    #search_fields = ('brand__brand_name','state__state_name','supplier__shop_owner__first_name')
    list_filter = [BrandSearch,StateSearch ,SupplierSearch,('po_creation_date', DateRangeFilter),('po_validity_date', DateRangeFilter),POAmountSearch,PORaisedBy]
    form = POGenerationForm

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        flag = 0
        new_order = ''
        for instance in instances:

            instance.last_modified_by = request.user
            instance.save()
            print(instance.cart)
            #Save Order
            #order,_ = Order.objects.get_or_create(ordered_cart=instance.cart)
            order,_ = Order.objects.get_or_create(ordered_cart=instance.cart,order_no=instance.cart.po_no)
            order.ordered_by=request.user
            order.order_status='ordered_to_brand'
            order.last_modified_by=request.user
            order.save()

            #Save OrderItem
            if OrderItem.objects.filter(order=order,ordered_product=instance.cart_product).exists():
                OrderItem.objects.filter(order=order,ordered_product=instance.cart_product).delete()

            order_item = OrderItem()
            order_item.ordered_product = instance.cart_product
            order_item.ordered_qty = instance.qty
            order_item.ordered_price = instance.price

            order_item.order = order
            order_item.last_modified_by = request.user
            order_item.save()

            #instance.order_brand.ordered_by = request.user
            #instance.order_brand.order_status = 'ordered_to_brand'
            #nstance.order_brand.brand_order_id = 'BRAND/ORDER/' + str(instance.order_brand.id)
            #new_order = instance.order_brand

            #Order.objects.get_or_create('ordered_cart'=instance.cart_list)
            #instance.order_brand.save()
            #instance.cart_id = 'BRAND-' + "{%Y%m%d}".format(today) + "-" + instance.id
            #instance.shop = Shop.objects.get(name='Gramfactory')

        # if request.user.groups.filter(name='grn_brand_to_gram_group').exists():
        #     if new_order and CartToBrand.objects.filter(order_brand=new_order):
        #         new_order.order_status = 'partially_delivered'
        #     elif new_order:
        #         new_order.order_status = 'delivered'
        #     new_order.save()
        formset.save_m2m()

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
        fields = ('product','product_invoice_price','manufacture_date','expiry_date','available_qty','ordered_qty','delivered_qty','returned_qty','damaged_qty')
        readonly_fields = ('product')

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
    #fields = [get_product]
    exclude = ('last_modified_by','available_qty',)

    # def get_formset(self, request, obj=None, **kwargs):
    #     initial = []
    #     print(request.method)
    #     if request.method == "GET":
    #         initial.append({
    #             'label': 'product',
    #         })
    #     #self.fields['product'] = Product.objects.get(id=4)
    #     formset = super(GRNOrderProductMappingAdmin, self).get_formset(request, obj, **kwargs)
    #     formset.__init__ = curry(formset.__init__, initial=initial)
    #     return formset

    # def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
    #     order_id = request.GET.get('odr')
    #
    #     if db_field.name == 'product':
    #         kwargs['queryset'] = Product.objects.filter(product_order_item__order__id=order_id)
    #
    #     return super(GRNOrderProductMappingAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class BrandNoteAdmin(admin.TabularInline):
    model = BrandNote
    exclude = ('order','last_modified_by')
    extra = 0

class OrderItemAdmin(admin.ModelAdmin):
    #search_fields = ('order__id','order__order_no','ordered_qty')
    list_filter = [OrderSearch , QuantitySearch, PORaisedBy ,('order__ordered_cart__po_creation_date', DateRangeFilter)]
    #date_hierarchy = 'created_at'
    list_display = ('order','ordered_product','ordered_qty','item_status','total_delivered_qty','total_damaged_qty','po_creation_date')

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

    def edit_grn_link(self, obj):
        #return format_html("<ul class ='object-tools'><li><a href = '/admin/gram_to_brand/grnorder/add/?brand=%s' class ='addlink' > Add order</a></li></ul>"% (obj.id))
        return format_html("<a href = '/admin/gram_to_brand/grnorder/%s/change/?order=%s&odr=%s' class ='addlink' > Edit GRN</a>"% (obj.id,obj.id,obj.id))

    edit_grn_link.short_description = 'Edit GRN'
    
    def __init__(self, *args, **kwargs):
        super(GRNOrderAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = None

    def get_form(self, request, obj=None, **kwargs):
        #request.current_object = obj
        return super(GRNOrderAdmin, self).get_form(request, obj, **kwargs)

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        order_id = 0
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
                instance.grn_order.order.order_status='partially_delivered'
                instance.grn_order.order.save()
                order_id = instance.grn_order.order.id

                #instance.available_qty = instance.delivered_qty
                instance.save()
            #Update Order
        if order_id!= 0 and OrderItem.objects.filter(order=order_id).exists():
            order = Order.objects.get(id=order_id)
            order_item = OrderItem.objects.filter(order=order_id)
            order.order_status = 'partially_delivered' if order_item.filter(item_status='partially_delivered').count()>0 else 'delivered'
            order.save()

        formset.save_m2m()


class OrderAdmin(admin.ModelAdmin):
    search_fields = ('id','order_no')
    list_display = ('order_no','order_status','ordered_by','created_at','add_grn_link')

    def add_grn_link(self, obj):
        #return format_html("<ul class ='object-tools'><li><a href = '/admin/gram_to_brand/grnorder/add/?brand=%s' class ='addlink' > Add order</a></li></ul>"% (obj.id))
        return format_html("<a href = '/admin/gram_to_brand/grnorder/add/?order=%s&odr=%s' class ='addlink' > Add GRN</a>"% (obj.id,obj.id))

    add_grn_link.short_description = 'Do GRN'

admin.site.register(Order,OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(GRNOrder,GRNOrderAdmin)


from django.utils.functional import curry
from django.forms import formset_factory
#from django import OrderShipmentFrom
from django.forms import BaseFormSet
from django.forms.models import BaseModelFormSet ,BaseInlineFormSet
#from .forms import OrderShipmentFrom





