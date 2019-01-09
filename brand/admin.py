from django.contrib import admin
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline
from .models import Brand, BrandData,BrandPosition,Vendor
from products.models import ProductVendorMapping
from retailer_backend.admin import InputFilter
from django.db.models import Q
from import_export.admin import ExportActionMixin
from .resources import BrandResource


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



from .forms import VendorForm
class BrandDataInline(SortableStackedInline):
    model = BrandData

class BrandPositionAdmin(NonSortableParentAdmin):
    inlines = [BrandDataInline]

admin.site.register(BrandPosition, BrandPositionAdmin)

class BrandAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = BrandResource
    fields = ('brand_name','brand_slug','brand_logo','brand_parent','brand_description','brand_code','active_status')
    list_display = ('id','brand_name','brand_logo','brand_code','active_status')
    list_filter = (BrandSearch,BrandCodeSearch,'active_status', )
    search_fields= ('brand_name','brand_code')
    prepopulated_fields = {'brand_slug': ('brand_name',)}

admin.site.register(Brand,BrandAdmin)

class ProductAdmin(admin.TabularInline):
    model = ProductVendorMapping
    #fields = ('brand_name',)

class VendorAdmin(admin.ModelAdmin):
    form = VendorForm
    inlines = [ProductAdmin]
    search_fields= ('vendor_name',)

admin.site.register(Vendor,VendorAdmin)
