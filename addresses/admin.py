from django.contrib import admin
from .models import Country,State,City,Address,Area,InvoiceCityMapping
from .forms import AddressForm, StateForm
# Register your models here.

class StateAdmin(admin.ModelAdmin):
    fields = ('country', 'state_name', 'state_code', 'status')
    list_display = ('country', 'state_name', 'state_code',  'status')
    list_filter = ('country', 'state_name', 'status')
    search_fields = ('state_name','state_code',)
    form = StateForm


class CityAdmin(admin.ModelAdmin):
    search_fields = ('city_name',)


class AddressAdmin(admin.ModelAdmin):
    form = AddressForm


class InvoiceCityMappingAdmin(admin.ModelAdmin):
    fields = ('city', 'city_code')
    list_display = ('city', 'city_code')


admin.site.register(Country)
admin.site.register(Area)
admin.site.register(City, CityAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(InvoiceCityMapping, InvoiceCityMappingAdmin)
