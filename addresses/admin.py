from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin

from import_export.admin import ImportExportModelAdmin

from .models import (
    Country, State, City, Address, Area, InvoiceCityMapping, Pincode, DispatchCenterCityMapping,
    DispatchCenterPincodeMapping, Route
)
from .forms import AddressForm, StateForm
from .resources import PincodeResource
from .views import RouteAutocomplete


class CityFilter(AutocompleteFilter):
    title = 'City'
    field_name = 'city'


class StateAdmin(admin.ModelAdmin):
    fields = ('country', 'state_name', 'state_code', 'status')
    list_display = ('country', 'state_name', 'state_code', 'status')
    list_filter = ('country', 'state_name', 'status')
    search_fields = ('state_name', 'state_code',)
    form = StateForm


class PincodeAdmin(ImportExportModelAdmin):
    list_select_related = ('city',)
    list_display = ('pincode', 'city')
    autocomplete_fields = ('city',)
    search_fields = ('city__city_name', 'pincode')
    resource_class = PincodeResource


class RouteInlineAdmin(admin.TabularInline):
    model = Route
    fields = ('city', 'name')
    extra = 1


class CityAdmin(admin.ModelAdmin):
    list_display = ('city_name', 'state', 'routes',)
    search_fields = ('city_name',)
    inlines = [RouteInlineAdmin]

    def routes(self, obj):
        return ", ".join(obj.city_routes.values_list('name', flat=True))

    def get_urls(self):
        from django.conf.urls import url
        urls = super(CityAdmin, self).get_urls()
        urls = [
           url(
               r'^route-autocomplete/$',
               self.admin_site.admin_view(RouteAutocomplete.as_view()),
               name="route_autocomplete"
           ),
        ] + urls
        return urls


class AddressAdmin(admin.ModelAdmin):
    form = AddressForm
    fields = ('nick_name', 'address_contact_name', 'address_contact_number',
              'address_type', 'address_line1', 'state', 'city', 'pincode_link')
    raw_id_fields = ('shop_name',)


class InvoiceCityMappingAdmin(admin.ModelAdmin):
    fields = ('city', 'city_code')
    list_display = ('city', 'city_code')


class DispatchCenterCityMappingAdmin(admin.ModelAdmin):
    fields = ('city', 'dispatch_center')
    list_display = ('city', 'dispatch_center')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DispatchCenterPincodeMappingAdmin(admin.ModelAdmin):
    fields = ('pincode', 'dispatch_center')
    list_display = ('pincode', 'dispatch_center')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RouteAdmin(admin.ModelAdmin):
    fields = ('city', 'name')
    list_display = ('city', 'name')
    list_filter = (CityFilter,)
    search_fields = ('city__city_name', 'name')


admin.site.register(Country)
admin.site.register(Area)
admin.site.register(City, CityAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(InvoiceCityMapping, InvoiceCityMappingAdmin)
admin.site.register(DispatchCenterCityMapping, DispatchCenterCityMappingAdmin)
admin.site.register(DispatchCenterPincodeMapping, DispatchCenterPincodeMappingAdmin)
admin.site.register(Pincode, PincodeAdmin)
admin.site.register(Route, RouteAdmin)

