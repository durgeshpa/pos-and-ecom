from django.contrib import admin

# Register your models here.
from nested_admin.nested import NestedTabularInline

from retailer_incentive.forms import SchemeCreationForm, SchemeSlabCreationForm, SchemeShopMappingCreationForm
from retailer_incentive.models import Scheme, SchemeSlab, SchemeShopMapping


class SchemeSlabAdmin(NestedTabularInline):
    model = SchemeSlab
    form = SchemeSlabCreationForm
    list_display = ('min_value', 'max_value','discount_value', 'discount_type')


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    model = Scheme
    form = SchemeCreationForm
    list_display =  ('name', 'start_date','end_date', 'is_active')
    inlines = [SchemeSlabAdmin, ]


@admin.register(SchemeShopMapping)
class SchemeShopMappingAdmin(admin.ModelAdmin):
    model = SchemeShopMapping
    form = SchemeShopMappingCreationForm
    fields = ('scheme', 'shop','is_active')
    list_display = ('scheme', 'shop', 'is_active')