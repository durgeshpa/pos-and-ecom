from products.models import ProductVendorMapping
from retailer_backend.admin import InputFilter
from dal import autocomplete

class BulkTaxUpdatedBySearch(InputFilter):
    parameter_name = 'updated_by'
    title = 'Updated By(Mob. No.)'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                updated_by__phone_number__icontains=self.value()
            )
