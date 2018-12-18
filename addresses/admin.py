from django.contrib import admin
from .models import Country,State,City,Address,Area
# Register your models here.
admin.site.register(Country)


class StateAdmin(admin.ModelAdmin):
    fields = ('country', 'state_name', 'status')
    list_display = ('country', 'state_name',  'status')
    list_filter = ('country', 'state_name',  'status')
    search_fields= ('state_name',)
admin.site.register(State, StateAdmin)
admin.site.register(City)
admin.site.register(Address)
admin.site.register(Area)
