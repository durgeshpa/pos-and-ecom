from django.contrib import admin
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline
from .models import Category,CategoryData,CategoryPosation
from import_export.admin import ExportActionMixin
from .resources import CategoryResource

class CategoryDataInline(SortableStackedInline):
    model = CategoryData

class CategoryPosationAdmin(NonSortableParentAdmin):
    inlines = [CategoryDataInline]

admin.site.register(CategoryPosation, CategoryPosationAdmin)


class CategoryAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = CategoryResource
    list_display = ['id','category_name', 'category_slug']
    search_fields = ['category_name']
    prepopulated_fields = {'category_slug': ('category_name',)}
    search_fields = ('category_name',)

admin.site.register(Category,CategoryAdmin)
