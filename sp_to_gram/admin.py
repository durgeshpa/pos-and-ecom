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
#
from dal import autocomplete
from django import forms
from addresses.models import State
from shops.models import Shop,ShopType

class POGenerationForm(forms.ModelForm):
    state = forms.ModelChoiceField(
        queryset=State.objects.all(),
        widget=autocomplete.ModelSelect2(url='state-autocomplete',)
    )
    gram_factory = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='gf'),
        widget=autocomplete.ModelSelect2(url='gf-shop-autocomplete', forward=('state',))
    )

    class Media:
        js = ('/static/admin/js/sp_po_generation_form.js',)

    class Meta:
        model = Cart
        fields = ('state','gram_factory','po_validity_date','payment_term','delivery_term')



class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'shop', 'po_status', 'last_modified_by')
    autocomplete_fields = ('brand',)
    list_display = ('po_no', 'brand', 'po_creation_date', 'po_validity_date', 'po_amount', 'po_raised_by', 'po_status')
    list_filter = [BrandFilter, ('po_creation_date', DateRangeFilter),
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
    list_display = ('invoice_no','vehicle_no','shipped_by','received_by')
    exclude = ('shipped_by','received_by','last_modified_by',)
    autocomplete_fields = ('order',)

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
