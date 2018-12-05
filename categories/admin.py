from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline
from .models import Category,CategoryData,CategoryPosation


class CategoryDataInline(SortableStackedInline):
    model = CategoryData

class CategoryPosationAdmin(NonSortableParentAdmin):
    inlines = [CategoryDataInline]

admin.site.register(CategoryPosation, CategoryPosationAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'category_slug']
    search_fields = ['category_name']
    prepopulated_fields = {'category_slug': ('category_name',)}

admin.site.register(Category,CategoryAdmin)

# from mptt.admin import DraggableMPTTAdmin
#
# class CategoriesAdmin(DraggableMPTTAdmin):
#     mptt_indent_field = "category_name"
#     list_display = ('category_name', 'category_parent','is_created', 'status')
#     list_display_links = ('category_name',)
#
# admin.site.register(Categories,CategoriesAdmin)
