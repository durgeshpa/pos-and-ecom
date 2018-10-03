from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline

from .models import Banner, BannerData,BannerPosition


class BannerDataInline(SortableStackedInline):
    model = BannerData

class BannerPositionAdmin(NonSortableParentAdmin):
    inlines = [BannerDataInline]

admin.site.register(BannerPosition, BannerPositionAdmin)

class BannerAdmin(admin.ModelAdmin):
    fields = ('name','image','status','banner_start_date','banner_end_date', 'Type','alt_text','text_below_image')
    list_display = ('id','name','image', 'created_at','updated_at','status')
    list_filter = ('name','image', 'created_at','updated_at')
    search_fields= ('name', 'created_at','updated_at')

admin.site.register(Banner,BannerAdmin)

# from mptt.admin import DraggableMPTTAdmin
#
# class CategoriesAdmin(DraggableMPTTAdmin):
#     mptt_indent_field = "category_name"
#     list_display = ('category_name', 'category_parent','is_created', 'status')
#     list_display_links = ('category_name',)
#
# admin.site.register(Categories,CategoriesAdmin)
