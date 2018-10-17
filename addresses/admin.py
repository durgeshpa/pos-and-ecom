from django.contrib import admin
from .models import Country,State,City,Address,Area
# Register your models here.
admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
admin.site.register(Address)
admin.site.register(Area)
