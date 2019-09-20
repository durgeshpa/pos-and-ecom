from django.contrib import admin

from import_export.admin import ImportExportModelAdmin

from .models import (
    Country, State, City, Address, Area, InvoiceCityMapping, Pincode
)
from .forms import AddressForm, StateForm
from .resources import PincodeResource


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


class CityAdmin(admin.ModelAdmin):
    search_fields = ('city_name',)


class AddressAdmin(admin.ModelAdmin):
    form = AddressForm
    fields = ('nick_name', 'address_contact_name', 'address_contact_number',
              'address_type', 'address_line1', 'state', 'city', 'pincode_link')
    raw_id_fields = ('shop_name',)


class InvoiceCityMappingAdmin(admin.ModelAdmin):
    fields = ('city', 'city_code')
    list_display = ('city', 'city_code')


admin.site.register(Country)
admin.site.register(Area)
admin.site.register(City, CityAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(InvoiceCityMapping, InvoiceCityMappingAdmin)
admin.site.register(Pincode, PincodeAdmin)

