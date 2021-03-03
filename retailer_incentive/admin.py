from django.contrib import admin

# Register your models here.
from nested_admin.nested import NestedTabularInline

from retailer_incentive.forms import SchemeCreationForm, SchemeSlabCreationForm
from retailer_incentive.models import Scheme, SchemeSlab



class SchemeSlabAdmin(NestedTabularInline):
    model = SchemeSlab
    form = SchemeSlabCreationForm
    fields = ('min_value', 'max_value','discount_value', 'discount_type')


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    model = Scheme
    form = SchemeCreationForm
    fields = ['name', 'start_date','end_date', 'is_active']
    inlines = [SchemeSlabAdmin, ]