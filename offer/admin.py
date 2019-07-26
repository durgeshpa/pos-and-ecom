from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline

from .models import OfferBanner, OfferBannerData,OfferBannerPosition, OfferBannerSlot, OfferPage, TopSKU
from.forms import OfferBannerForm, OfferBannerPositionForm
class OfferBannerDataInline(SortableStackedInline):
    model = OfferBannerData

class OfferBannerPositionAdmin(NonSortableParentAdmin):
    form=OfferBannerPositionForm
    inlines = [OfferBannerDataInline]



admin.site.register(OfferBannerPosition, OfferBannerPositionAdmin)

class OfferBannerAdmin(admin.ModelAdmin):
    fields = ('name','image','offer_banner_type','category','sub_category','brand','sub_brand','products','status','offer_banner_start_date','offer_banner_end_date','alt_text','text_below_image')
    list_display = ('id','name','image','offer_banner_start_date','offer_banner_end_date','created_at','status')
    list_filter = ('name','image', 'created_at','updated_at')
    search_fields= ('name', 'created_at','updated_at')
    form = OfferBannerForm



admin.site.register(OfferBanner,OfferBannerAdmin)

class OfferBannerSlotAdmin(admin.ModelAdmin):
    fields = ('page','name')
    list_display = ('name','page')
    list_filter = ('page','name')
    search_fields= ('page','name')

admin.site.register(OfferBannerSlot,OfferBannerSlotAdmin)

class OfferPageAdmin(admin.ModelAdmin):
    field = ('name')

admin.site.register(OfferPage,OfferPageAdmin)

class TopSKUAdmin(admin.ModelAdmin):
    fields = ('product', 'start_date', 'end_date', 'status',)
    list_display = ('product', 'start_date', 'end_date', 'status',)
    list_filter = ('product', 'start_date', 'end_date', 'status',)
    search_fields = ('product', 'start_date', 'end_date', 'status',)

admin.site.register(TopSKU,TopSKUAdmin)
