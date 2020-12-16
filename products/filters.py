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


class SourceSKUSearch(InputFilter):
    parameter_name = 'source_sku'
    title = 'Source SKU ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            source_sku = self.value()
            if source_sku is None:
                return
            return queryset.filter(
                source_sku__product_sku__icontains=source_sku
            )


class SourceSKUName(InputFilter):
    parameter_name = 'source_sku_name'
    title = 'Source SKU Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            source_sku_name = self.value()
            if source_sku_name is None:
                return
            return queryset.filter(
                source_sku__product_name__icontains=source_sku_name
            )


class DestinationSKUName(InputFilter):
    parameter_name = 'destination_sku_name'
    title = 'Destination SKU Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            destination_sku_name = self.value()
            if destination_sku_name is None:
                return
            return queryset.filter(
                destination_sku__product_name__icontains=destination_sku_name
            )


class DestinationSKUSearch(InputFilter):
    parameter_name = 'destination_sku'
    title = 'Destination SKU ID'

    def queryset(self, request, queryset):
        if self.value() is not None:
            destination_sku = self.value()
            if destination_sku is None:
                return
            return queryset.filter(
                destination_sku__product_sku__icontains=destination_sku
            )
