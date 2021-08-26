from django.contrib import admin

# Register your models here.
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline
from .models import Banner, BannerData,BannerPosition, BannerSlot, Page, HomePageMessage
from.forms import BannerForm, BannerPositionForm, BannerDataPosition
from .views import (BannerDataAutocomplete, BannerShopAutocomplete,
                    RetailerShopAutocomplete, PincodeAutocomplete, CityAutocomplete)
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.utils.safestring import mark_safe
from django.conf.urls import url
from retailer_backend.filters import SellerShopFilter, CityFilter

class BannerDataInline(SortableStackedInline):
    model = BannerData
    form = BannerDataPosition

class BannerPositionAdmin(NonSortableParentAdmin):
    form=BannerPositionForm
    inlines = [BannerDataInline]
    list_display = ('shop', 'page', 'bannerslot', 'city_list', 'pincode_list', 'buyer_shop_list')
    list_filter = (SellerShopFilter,)

    def get_urls(self):
        urls = super(BannerPositionAdmin, self).get_urls()
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

    class Media:
        pass

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

class HomePageMessageAdmin(admin.ModelAdmin):
    field = ('message', 'is_active')


admin.site.register(Page,PageAdmin)
admin.site.register(Banner,BannerAdmin)
admin.site.register(BannerSlot,BannerSlotAdmin)
admin.site.register(BannerPosition, BannerPositionAdmin)
admin.site.register(HomePageMessage, HomePageMessageAdmin)