from django.contrib import admin
from .models import Cart,CartProductMapping,Order,OrderedProduct,OrderedProductMapping,OrderedProductReserved
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from .forms import CartProductMappingForm,POGenerationForm
from retailer_backend.filters import BrandFilter,SupplierFilter,POAmountSearch,PORaisedBy
from daterange_filter.filter import DateRangeFilter
from django.utils.html import format_html
from django.urls import reverse


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    autocomplete_fields = ('cart_product',)
    search_fields =('cart_product',)
    form = CartProductMappingForm


# class CartProductMappingAdmin(admin.TabularInline):
#     model = CartProductMapping
#     autocomplete_fields = ('cart_product',)
#     exclude = ('qty',)
#
#     def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
#         #print(db_field)
#         if db_field.name == 'cart_product':
#             pass
#             #kwargs['queryset'] = Product.objects.filter(product_grn_order_product__delivered_qty__gt=0)
#             #print(Product.objects.filter(product_grn_order_product__delivered_qty__gt=0).product_grn_order_product)
#             #print(GRNOrderProductMapping.objects.filter(delivered_qty__gt=0).query)
#         return super(CartProductMappingAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

from dal import autocomplete
from django import forms
from addresses.models import State
from shops.models import Shop,ShopType

class POGenerationForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='my-shop-autocomplete',)
    )

    class Media:
        js = ('/static/admin/js/sp_po_generation_form.js',)

    class Meta:
        model = Cart
        fields = ('shop','po_validity_date','payment_term','delivery_term')

class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'po_status', 'last_modified_by')
    #autocomplete_fields = ('brand',)
    list_display = ('po_no', 'po_creation_date', 'po_validity_date', 'po_amount', 'po_raised_by', 'po_status')
    list_filter = [('po_creation_date', DateRangeFilter),
                   ('po_validity_date', DateRangeFilter), POAmountSearch, PORaisedBy]
    form = POGenerationForm

    def download_purchase_order(self, obj):
        if obj.is_approve:
            return format_html("<a href= '%s' >Download PO</a>" % (reverse('download_purchase_order', args=[obj.pk])))
    download_purchase_order.short_description = 'Download Purchase Order'

    class Media:
        js = ('/static/admin/js/sp_po_generation_form.js',)


admin.site.register(Cart,CartAdmin)

class OrderAdmin(admin.ModelAdmin):
    search_fields = ('order',)
    list_display = ('order_no','order_status',)

admin.site.register(Order,OrderAdmin)

class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    exclude = ('last_modified_by','ordered_qty','available_qty','reserved_qty')

class OrderedProductAdmin(admin.ModelAdmin):
    inlines = [OrderedProductMappingAdmin]
    list_display = ('invoice_no','vehicle_no','shipped_by','received_by',)
    exclude = ('shipped_by','received_by','last_modified_by',)
    autocomplete_fields = ('order',)

    warehouse_user_fields = ['order','invoice_no','vehicle_no',]
    delivery_user_fields = ['order','vehicle_no',]

    warehouse_user_fieldset = ['product', 'manufacture_date', 'expiry_date','shipped_qty',]
    delivery_user_fieldset = ['product', 'manufacture_date', 'expiry_date','delivered_qty','returned_qty','damaged_qty',]

    # warehouse_user_fieldset = (
    #     ((None), {'fields': ('product', 'manufacture_date', 'expiry_date','shipped_qty')}),
    # )

    def get_formsets_with_inlines(self, request, obj=None):
        for inline in self.get_inline_instances(request, obj):
            # hide MyInline in the add view
            if isinstance(inline, OrderedProductMappingAdmin) and obj not in self.warehouse_user_fieldset:
                yield inline.get_formset(request, obj), inline

    # def get_fieldsets(self, request, obj=None, **kwargs):
    #     if request.user.is_superuser:
    #         return self.warehouse_user_fieldset
    #     return super(OrderedProductAdmin, self).get_fieldsets(request, obj, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = []

        if request.user.is_superuser:
            self.fields = self.warehouse_user_fields
        elif request.user.has_perm('sp_to_gram.warehouse_shipment'):
            self.fields = self.warehouse_user_fields
        elif request.user.has_perm('sp_to_gram.delivery_from_gf'):
            self.fields = self.delivery_user_fields

        return super(OrderedProductAdmin, self).get_form(request, obj, **kwargs)

    # def get_fieldsets(self, request, obj=None, **kwargs):
    #     if request.user.has_perm('sp_to_gram.warehouse_shipment'):
    #         self.fieldsets = self.warehouse_user_fieldset
    #     elif request.user.has_perm('sp_to_gram.delivery_from_gf'):
    #         self.fields = self.delivery_user_fieldset
    #     else:
    #         self.fields = self.delivery_user_fieldset
    #     return super(OrderedProductAdmin, self).get_fieldsets(request, obj, **kwargs)

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        for instance in instances:
            instance.available_qty = instance.delivered_qty
            instance.save()
        formset.save_m2m()

admin.site.register(OrderedProduct,OrderedProductAdmin)

class OrderedProductMappingAdmin2(admin.ModelAdmin):
    list_display = ('ordered_product','product','ordered_qty','available_qty',)

admin.site.register(OrderedProductMapping,OrderedProductMappingAdmin2)

class OrderedProductReservedAdmin(admin.ModelAdmin):
    list_display = ('order_product_reserved','product','cart','reserved_qty','order_reserve_end_time','created_at')

admin.site.register(OrderedProductReserved,OrderedProductReservedAdmin)
