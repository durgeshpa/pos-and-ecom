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

class CartAdmin(admin.ModelAdmin):
    template = 'admin/sp_to_gram/cart/change_form.html'
    inlines = [CartProductMappingAdmin]
    exclude = ('po_no', 'po_status', 'last_modified_by')
    #autocomplete_fields = ('brand',)
    list_display = ('po_no', 'po_creation_date', 'po_validity_date', 'po_amount', 'po_raised_by', 'po_status')
    list_filter = [('po_creation_date', DateRangeFilter),
                   ('po_validity_date', DateRangeFilter), POAmountSearch, PORaisedBy]
    form = POGenerationForm

    def download_purchase_order(self, obj):
        if obj.is_approve:
            return format_html("<a href= '%s' >Download PO</a>" % (reverse('download_purchase_order_sp', args=[obj.pk])))
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

    warehouse_user_fieldset = ['product', 'manufacture_date', 'expiry_date','shipped_qty',]
    delivery_user_fieldset = ['product', 'manufacture_date', 'expiry_date', 'delivered_qty', 'returned_qty',
                              'damaged_qty', ]

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
    list_display = ('invoice_no','vehicle_no','shipped_by','received_by',)
    exclude = ('shipped_by','received_by','last_modified_by',)
    autocomplete_fields = ('order',)

    warehouse_user_fields = ['order','invoice_no','vehicle_no',]
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

admin.site.register(OrderedProduct,OrderedProductAdmin)

class OrderedProductMappingAdmin2(admin.ModelAdmin):
    list_display = ('ordered_product','product','ordered_qty','available_qty',)

admin.site.register(OrderedProductMapping,OrderedProductMappingAdmin2)

class OrderedProductReservedAdmin(admin.ModelAdmin):
    list_display = ('order_product_reserved','product','reserved_qty','order_reserve_end_time','created_at','reserve_status')

admin.site.register(OrderedProductReserved,OrderedProductReservedAdmin)
