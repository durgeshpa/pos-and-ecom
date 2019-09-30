from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline
from .models import Banner, BannerData,BannerPosition, BannerSlot, Page, BannerLocation
from.forms import BannerForm, BannerPositionForm, BannerDataPosition, BannerLocationForm
from .views import (BannerDataAutocomplete, BannerShopAutocomplete,
                    RetailerShopAutocomplete, PincodeAutocomplete, CityAutocomplete)
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .resources import BannerLocationResource
from django.utils.safestring import mark_safe
from django.conf.urls import url

class BannerDataInline(SortableStackedInline):
    model = BannerData
    form = BannerDataPosition

class BannerPositionAdmin(NonSortableParentAdmin):
    form=BannerPositionForm
    inlines = [BannerDataInline]

class BannerAdmin(admin.ModelAdmin):
    fields = ('name','image','banner_type','category','sub_category','brand','sub_brand','products','status','banner_start_date','banner_end_date','alt_text','text_below_image')
    list_display = ('id','name','image','banner_start_date','banner_end_date','created_at','status')
    list_filter = ('name','image', 'created_at','updated_at')
    search_fields= ('name', 'created_at','updated_at')
    form = BannerForm

class BannerSlotAdmin(admin.ModelAdmin):
    fields = ('page','name')
    list_display = ('name','page')
    list_filter = ('page','name')
    search_fields= ('page','name')

class PageAdmin(admin.ModelAdmin):
    field = ('name')

class BannerLocationAdmin(ImportExportModelAdmin):
    resource_class = BannerLocationResource
    form = BannerLocationForm
    list_display = ('id', 'banner', 'buyer_shop','city','pincode','banner_img')

    def get_urls(self):
        urls = super(BannerLocationAdmin, self).get_urls()
        urls = [
            url(
                r'^retailer-shop-autocomplete/$',
                self.admin_site.admin_view(RetailerShopAutocomplete.as_view()),
                name="retailer-shop-autocomplete"
            ),
            url(
               r'^pincode-autocomplete/$',
               self.admin_site.admin_view(PincodeAutocomplete.as_view()),
               name="pincode-autocomplete"
            ),
            url(
               r'^city-autocomplete/$',
               self.admin_site.admin_view(CityAutocomplete.as_view()),
               name="city-autocomplete"
            ),
        ] + urls
        return urls

    def banner_img(self,obj):
        return mark_safe('<a href="{}" target="blank"><img alt="{}" src="{}" height="50px" width="50px"/></a>'.
                format(obj.banner.image.url, obj.banner.alt_text, obj.banner.image.url))

admin.site.register(Page,PageAdmin)
admin.site.register(Banner,BannerAdmin)
admin.site.register(BannerSlot,BannerSlotAdmin)
admin.site.register(BannerPosition, BannerPositionAdmin)
admin.site.register(BannerLocation, BannerLocationAdmin)