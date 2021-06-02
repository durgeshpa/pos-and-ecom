from django.contrib import admin
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline
from .models import Brand, BrandData,BrandPosition,Vendor
from products.models import ProductVendorMapping
from retailer_backend.admin import InputFilter
from django.db.models import Q
from import_export.admin import ExportActionMixin
from .resources import BrandResource
from products.admin import ExportCsvMixin
from admin_auto_filters.filters import AutocompleteFilter
from .forms import BrandForm
from .views import SearchProduct

class BrandSearch(InputFilter):
    parameter_name = 'brand_name'
    title = 'Brand Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            brand_name = self.value()
            if brand_name is None:
                return
            return queryset.filter(
                Q(brand_name__icontains=brand_name)
            )

class BrandCodeSearch(InputFilter):
    parameter_name = 'brand_code'
    title = 'Brand Code'

    def queryset(self, request, queryset):
        if self.value() is not None:
            brand_code = self.value()
            if brand_code is None:
                return
            return queryset.filter(
                Q(brand_code__icontains=brand_code)
            )

class VendorNameSearch(InputFilter):
    parameter_name = 'vendor_name'
    title = 'Vendor Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            vendor_name = self.value()
            if vendor_name is None:
                return
            return queryset.filter(
                Q(vendor_name__icontains=vendor_name)
            )

class VendorContactNoSearch(InputFilter):
    parameter_name = 'mobile'
    title = 'Vendor Contact No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            mobile = self.value()
            if mobile is None:
                return
            return queryset.filter(
                Q(mobile__icontains=mobile)
            )

class StateFilter(AutocompleteFilter):
    title = 'State' # display title
    field_name = 'state' # name of the foreign key field

class CityFilter(AutocompleteFilter):
    title = 'City' # display title
    field_name = 'city' # name of the foreign key field

from .forms import VendorForm
class BrandDataInline(SortableStackedInline):
    model = BrandData

class BrandPositionAdmin(NonSortableParentAdmin):
    form=BrandForm
    inlines = [BrandDataInline]

class BrandAdmin( admin.ModelAdmin, ExportCsvMixin):
    resource_class = BrandResource
    actions = ["export_as_csv"]
    fields = ('brand_name','brand_slug','brand_logo','brand_parent','brand_description','brand_code','categories',)
    list_display = ('id','brand_name','brand_logo','brand_code')
    list_filter = (BrandSearch,BrandCodeSearch, )
    search_fields= ('brand_name','brand_code')
    filter_horizontal = ('categories',)
    prepopulated_fields = {'brand_slug': ('brand_name',)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "brand_parent":
            kwargs["queryset"] = Brand.objects.all().order_by('brand_slug')
        return super(BrandAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class VendorAdmin(admin.ModelAdmin):
    form = VendorForm
    list_display = ('vendor_name', 'mobile','state', 'city','vendor_products_brand')
    search_fields = ('vendor_name',)
    list_filter = [VendorNameSearch, VendorContactNoSearch, StateFilter, CityFilter]

    class Media:
        pass

    def save_formset(self, request, form, formset, change):
        formset.save()
        form.instance.save()

    def get_urls(self):
        from django.conf.urls import url
        urls = super(VendorAdmin, self).get_urls()
        urls = [
            url(r'^search-product/$',
                self.admin_site.admin_view(SearchProduct.as_view()),
                name='search-product'),
        ] + urls
        return urls

    change_form_template = 'admin/brand/vendor/change_form.html'

admin.site.register(Vendor,VendorAdmin)
admin.site.register(Brand,BrandAdmin)
admin.site.register(BrandPosition, BrandPositionAdmin)