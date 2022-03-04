from django.contrib import admin
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline
from .models import Category, CategoryData, CategoryPosation, B2cCategory, B2cCategoryData
from import_export.admin import ExportActionMixin
from .resources import CategoryResource, B2cCategoryResource
from retailer_backend.admin import InputFilter
from django.db.models import Q


class CategorySearch(InputFilter):
    parameter_name = 'category_name'
    title = 'Category Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            category_name = self.value()
            if category_name is None:
                return
            return queryset.filter(
                Q(category_name__icontains=category_name)
            )


class CategoryParentSearch(InputFilter):
    parameter_name = 'category_parent'
    title = 'Category Parent'

    def queryset(self, request, queryset):
        if self.value() is not None:
            category_parent = self.value()
            if category_parent is None:
                return
            return queryset.filter(
                Q(category_parent__category_name__icontains=category_parent)
            )


class CategorySKUSearch(InputFilter):
    parameter_name = 'category_sku_part'
    title = 'Category Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            category_sku_part = self.value()
            if category_sku_part is None:
                return
            return queryset.filter(
                Q(category_sku_part__icontains=category_sku_part)
            )


class CategoryDataInline(SortableStackedInline):
    model = CategoryData

class B2cCategoryDataInline(SortableStackedInline):
    model = B2cCategoryData

class CategoryPosationAdmin(NonSortableParentAdmin):
    inlines = [CategoryDataInline, B2cCategoryDataInline]

admin.site.register(CategoryPosation, CategoryPosationAdmin)

class CategoryAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = CategoryResource
    fields = ('category_name', 'category_slug', 'category_desc', 'category_sku_part',
              'category_image', 'status', 'b2c_status')
    list_display = ['id', 'category_name', 'category_slug', 'category_sku_part','b2c_status']
    search_fields = ['category_name']
    prepopulated_fields = {'category_slug': ('category_name',)}
    search_fields = ('category_name',)
    list_filter = [CategorySearch, CategoryParentSearch, CategorySKUSearch]


class B2cCategoryAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = B2cCategoryResource
    fields = ('category_name', 'category_slug', 'category_desc', 'category_sku_part',
              'category_image', 'status')
    list_display = ['id', 'category_name', 'category_slug', 'category_sku_part']
    search_fields = ['category_name']
    prepopulated_fields = {'category_slug': ('category_name',)}
    search_fields = ('category_name',)
    list_filter = [CategorySearch, CategoryParentSearch, CategorySKUSearch]


admin.site.register(Category,CategoryAdmin)
admin.site.register(B2cCategory, B2cCategoryAdmin)