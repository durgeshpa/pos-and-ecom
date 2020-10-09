from django.contrib import admin
from .models import (Cart,CartProductMapping,Order,OrderedProduct,OrderedProductMapping,OrderedProductReserved,
                     StockAdjustment, StockAdjustmentMapping)
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from .forms import CartProductMappingForm,POGenerationForm, OrderedProductMappingForm
from retailer_backend.filters import BrandFilter,SupplierFilter,POAmountSearch,PORaisedBy
from daterange_filter.filter import DateRangeFilter
from django.utils.html import format_html
from django.urls import reverse
from admin_numeric_filter.admin import NumericFilterModelAdmin, SingleNumericFilter, RangeNumericFilter, \
    SliderNumericFilter
from dal_admin_filters import AutocompleteFilter
from retailer_backend.admin import InputFilter
from retailer_backend.filters import ProductFilter
from django.db.models import Q
from django_admin_listfilter_dropdown.filters import (ChoiceDropdownFilter, RelatedDropdownFilter, DropdownFilter)

class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    fields = ('cart_product','gf_code','ean_number','taxes','case_size','number_of_cases','scheme','price','total_price',)
    readonly_fields = ('gf_code','ean_number','taxes',)
    autocomplete_fields = ('cart_product',)
    search_fields =('cart_product',)
    form = CartProductMappingForm

#admin.site.register(CartProductMapping, CartProductMappingAdmin)
class RecipientWarehouseFilter(AutocompleteFilter):
    title = 'Recipient Warehouse'                    # filter's title
    field_name = 'shop'           # field name - ForeignKey to Country model
    autocomplete_url = 'my-shop-autocomplete' # url name of Country autocomplete view

class POSearch(InputFilter):
    parameter_name = 'po_no'
    title = 'PO No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            po_no = self.value()
            if po_no is None:
                return
            return queryset.filter(po_no__icontains=po_no)


class CartAdmin(NumericFilterModelAdmin,admin.ModelAdmin):
    template = 'admin/sp_to_gram/cart/change_form.html'
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'po_status', 'last_modified_by')
    #autocomplete_fields = ('brand',)
    list_display = ('po_no', 'po_creation_date', 'po_validity_date', 'po_amount', 'po_raised_by', 'po_status', 'download_purchase_order',)
    list_filter = [RecipientWarehouseFilter,POSearch,('po_creation_date', DateRangeFilter),
                   ('po_validity_date', DateRangeFilter), ('po_amount',RangeNumericFilter), PORaisedBy]
    form = POGenerationForm

    def download_purchase_order(self, obj):
        return format_html("<a href= '%s' >Download PO</a>" % (reverse('download_purchase_order_sp', args=[obj.pk])))
    download_purchase_order.short_description = 'Download Purchase Order'

    class Media:
        js = ('/static/admin/js/sp_po_generation_form.js',)
        pass


class OrderIdSearch(InputFilter):
    parameter_name = 'order_no'
    title = 'Order Id'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            if order_no is None:
                return
            return queryset.filter(order_no__icontains=order_no)


class OrderAdmin(admin.ModelAdmin):
    search_fields = ('order',)
    list_display = ('order_no','order_status',)
    list_filter = (OrderIdSearch,'order_status',)


class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    form = OrderedProductMappingForm
    exclude = ('last_modified_by','ordered_qty','reserved_qty')

    warehouse_user_fieldset = ['product', 'manufacture_date', 'expiry_date','shipped_qty',]
    delivery_user_fieldset = ['product', 'manufacture_date', 'expiry_date', 'delivered_qty', 'returned_qty',
                              'damaged_qty', 'batch_id']

    def get_fieldsets(self, request, obj=None, **kwargs):
        if request.user.is_superuser:
            self.fields = self.delivery_user_fieldset
        elif request.user.has_perm('sp_to_gram.warehouse_shipment'):
            self.fields = self.warehouse_user_fieldset
        elif request.user.has_perm('sp_to_gram.delivery_from_gf'):
            self.fields = self.delivery_user_fieldset

        return super(OrderedProductMappingAdmin, self).get_fieldsets(request, obj, **kwargs)

class OrderedProductAdmin(admin.ModelAdmin):
    inlines = [OrderedProductMappingAdmin]
    list_display = ('invoice_no','vehicle_no','shipped_by','received_by','status')
    exclude = ('shipped_by','received_by','last_modified_by',)
    autocomplete_fields = ('order',)

    warehouse_user_fields = ['order','invoice_no','vehicle_no', 'status']
    delivery_user_fields = ['order','vehicle_no',]

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = []

        if request.user.is_superuser:
            self.fields = self.warehouse_user_fields
        elif request.user.has_perm('sp_to_gram.warehouse_shipment'):
            self.fields = self.warehouse_user_fields
        elif request.user.has_perm('sp_to_gram.delivery_from_gf'):
            self.fields = self.delivery_user_fields

        return super(OrderedProductAdmin, self).get_form(request, obj, **kwargs)

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        for instance in instances:
            instance.available_qty = instance.delivered_qty
            instance.save()
        formset.save_m2m()


class OrderedProductMappingAdmin2(admin.ModelAdmin):
    list_display = ('ordered_product','product','ordered_qty','available_qty',)
    readonly_fields = ('shop', 'ordered_product', 'product','last_modified_by')
    list_filter = (ProductFilter, ('ordered_product__status', ChoiceDropdownFilter),)

    class Media:
        pass


class OrderedProductReservedAdmin(admin.ModelAdmin):
    list_select_related = ('cart', 'product')
    list_display = ('product', 'cart', 'reserved_qty', 'shipped_qty',
                    'order_reserve_end_time', 'created_at', 'reserve_status',
                    'grn_product_link')
    readonly_fields = ('cart', 'product',
                       'reserved_qty', 'shipped_qty', 'reserve_status')
    fields = ('cart', 'product', 'reserved_qty',
              'shipped_qty', 'reserve_status')

    def grn_product_link(self, obj):
        url = reverse("admin:sp_to_gram_orderedproductmapping_change", args=[obj.order_product_reserved_id])
        link = '<a href="%s" target="blank">%s</a>' % (url, obj.product)
        return format_html(link)
    grn_product_link.short_description = 'GRN Product'


admin.site.register(Cart,CartAdmin)
admin.site.register(StockAdjustment)
admin.site.register(Order,OrderAdmin)
admin.site.register(StockAdjustmentMapping)
admin.site.register(OrderedProduct,OrderedProductAdmin)
admin.site.register(OrderedProductMapping,OrderedProductMappingAdmin2)
admin.site.register(OrderedProductReserved,OrderedProductReservedAdmin)


