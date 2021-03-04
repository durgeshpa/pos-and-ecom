from django.contrib import admin

# Register your models here.
from nested_admin.nested import NestedTabularInline

from retailer_incentive.forms import SchemeCreationForm, SchemeSlabCreationForm, SchemeShopMappingCreationForm
from retailer_incentive.models import Scheme, SchemeSlab, SchemeShopMapping


class SchemeSlabAdmin(NestedTabularInline):
    model = SchemeSlab
    form = SchemeSlabCreationForm
    list_display = ('min_value', 'max_value','discount_value', 'discount_type')

    class Media:
        pass


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    """
    This class is used to get the Scheme data on admin
    """
    model = Scheme
    form = SchemeCreationForm
    list_display = ('name', 'start_date','end_date', 'is_active')
    inlines = [SchemeSlabAdmin, ]

    class Media:
        pass

@admin.register(SchemeShopMapping)
class SchemeShopMappingAdmin(admin.ModelAdmin):
    """
    This class is used to get the Scheme Shop Mapping data on admin
    """
    model = SchemeShopMapping
    form = SchemeShopMappingCreationForm
    list_display = ('scheme_id', 'scheme_name', 'shop', 'priority', 'is_active', 'user')

    def scheme_id(self, obj):
        return obj.scheme_id

    def scheme_name(self, obj):
        return obj.scheme.name

    class Media:
        pass