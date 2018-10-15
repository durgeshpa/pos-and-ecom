from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline

from .models import Banner, BannerData,BannerPosition, BannerSlot, Page

class BannerDataInline(SortableStackedInline):
    model = BannerData

class BannerPositionAdmin(NonSortableParentAdmin):
    inlines = [BannerDataInline]



admin.site.register(BannerPosition, BannerPositionAdmin)

class BannerAdmin(admin.ModelAdmin):
    fields = ('name','image','status','banner_start_date','banner_end_date','alt_text','text_below_image')
    list_display = ('id','name','image', 'created_at','updated_at','status')
    list_filter = ('name','image', 'created_at','updated_at')
    search_fields= ('name', 'created_at','updated_at')

admin.site.register(Banner,BannerAdmin)

class BannerSlotAdmin(admin.ModelAdmin):
    fields = ('page','name')
    list_display = ('name','page')
    list_filter = ('page','name')
    search_fields= ('page','name')

admin.site.register(BannerSlot,BannerSlotAdmin)

class PageAdmin(admin.ModelAdmin):
    field = ('name')

admin.site.register(Page,PageAdmin)
