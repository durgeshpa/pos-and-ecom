from django.contrib import admin
from .models import Country,State,City,Address,Area,InvoiceCityMapping

# Register your models here.
admin.site.register(Country)


class StateAdmin(admin.ModelAdmin):
    fields = ('country', 'state_name', 'status')
    list_display = ('country', 'state_name',  'status')
    list_filter = ('country', 'state_name',  'status')
    search_fields= ('state_name',)
admin.site.register(State, StateAdmin)
class CityAdmin(admin.ModelAdmin):
    search_fields= ('city_name',)
admin.site.register(City, CityAdmin)
admin.site.register(Area)

from .forms import AddressForm
class AddressAdmin(admin.ModelAdmin):
    form = AddressForm

admin.site.register(Address, AddressAdmin)

class InvoiceCityMappingAdmin(admin.ModelAdmin):
    fields = ('city','city_code')
    list_display = ('city','city_code')
admin.site.register(InvoiceCityMapping, InvoiceCityMappingAdmin)
