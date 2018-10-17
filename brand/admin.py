from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline

from .models import Brand, BrandData,BrandPosition


class BrandDataInline(SortableStackedInline):
    model = BrandData

class BrandPositionAdmin(NonSortableParentAdmin):
    inlines = [BrandDataInline]

admin.site.register(BrandPosition, BrandPositionAdmin)

class BrandAdmin(admin.ModelAdmin):
    fields = ('brand_name','brand_logo','brand_description','brand_code','active_status')
    list_display = ('brand_name','brand_logo','brand_code','active_status')
    list_filter = ('brand_name','brand_logo','brand_code','active_status', 'created_at','updated_at')
    search_fields= ('brand_name','brand_code')

admin.site.register(Brand,BrandAdmin)