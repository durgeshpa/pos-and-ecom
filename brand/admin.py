from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline

from .models import Brand, BrandData,BrandPosition,Vendor
from products.models import ProductVendorMapping
from retailer_backend.admin import InputFilter
from django.db.models import Q

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

class BrandAdmin(admin.ModelAdmin):
    fields = ('brand_name','brand_logo','brand_parent','brand_description','brand_code','active_status')
    list_display = ('brand_name','brand_logo','brand_code','active_status')
    list_filter = (BrandSearch,BrandCodeSearch,'active_status', )
    search_fields= ('brand_name','brand_code')

admin.site.register(Brand,BrandAdmin)

class ProductAdmin(admin.TabularInline):
    model = ProductVendorMapping
    #fields = ('brand_name',)

class VendorAdmin(admin.ModelAdmin):
    form = VendorForm
    inlines = [ProductAdmin]

admin.site.register(Vendor,VendorAdmin)
