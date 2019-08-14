from daterange_filter.filter import DateRangeFilter
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from admin_auto_filters.filters import AutocompleteFilter
from retailer_backend.admin import InputFilter
from django.db.models import Q


class BrandFilter(AutocompleteFilter):
    title = 'Brand' # display title
    field_name = 'brand' # name of the foreign key field


class SupplierStateFilter(AutocompleteFilter):
    title = 'State' # display title
    field_name = 'supplier_state' # name of the foreign key field


class SupplierFilter(AutocompleteFilter):
    title = 'Supplier' # display title
    field_name = 'supplier_name' # name of the foreign key field


class OrderSearch(InputFilter):
    parameter_name = 'order'
    title = 'PO No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order = self.value()
            if order is None:
                return
            return queryset.filter(
                Q(order__order_no__icontains=order)
            )

class QuantitySearch(InputFilter):
    parameter_name = 'qty'
    title = 'Ordered Qty'

    def queryset(self, request, queryset):
        if self.value() is not None:
            qty = self.value()
            if qty is None:
                return
            return queryset.filter(
                Q(ordered_qty__icontains=qty)
            )

class InvoiceNoSearch(InputFilter):
    parameter_name = 'invoice_no'
    title = 'Invoice No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            invoice_no = self.value()
            if invoice_no is None:
                return
            return queryset.filter(
                Q(invoice_no__icontains=invoice_no)
            )

class GRNSearch(InputFilter):
    parameter_name = 'grn_id'
    title = 'GRN No'

    def queryset(self, request, queryset):
        if self.value() is not None:
            grn_id = self.value()
            if grn_id is None:
                return
            return queryset.filter(
                Q(grn_id__icontains=grn_id)
            )

class POAmountSearch(InputFilter):
    parameter_name = 'po_amount'
    title = 'PO Amount'

    def queryset(self, request, queryset):
        if self.value() is not None:
            po_amount = self.value()
            if po_amount is None:
                return
            return queryset.filter(
                Q(po_amount=po_amount)
            )

class PORaisedBy(InputFilter):
    parameter_name = 'po_raised_by'
    title = 'PO Raised By'

    def queryset(self, request, queryset):
        if self.value() is not None:
            po_raised_by = self.value()
            if po_raised_by is None:
                return
            # return queryset.filter(
            #     Q(po_raised_by=po_raised_by)
            # )
            any_name = Q()
            for name in po_raised_by.split():
                any_name &= (
                    Q(po_raised_by__first_name__icontains=name) |
                    Q(po_raised_by__last_name__icontains=name)
                )
            return queryset.filter(any_name)

class ShopFilter(AutocompleteFilter):
    title = 'Shop'
    field_name = 'shop'
    autocomplete_url = 'admin:shop-autocomplete'


class ManagerFilter(InputFilter):
    title = 'Manager'
    parameter_name = 'manager'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(
                Q(manager__first_name__icontains=value) |
                  Q(manager__phone_number=value)
                )
        return queryset

class EmployeeFilter(InputFilter):
    title = 'Employee'
    parameter_name = 'employee'

    def queryset(self, request, queryset):
        value = self.value()
        if value :
            return queryset.filter(
                Q(employee__first_name__icontains=value) |
                  Q(employee__phone_number=value)
                )
        return queryset



