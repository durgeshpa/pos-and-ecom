import logging

from dal_admin_filters import AutocompleteFilter
from django.contrib import admin
from audit.forms import AuditCreationForm
from audit.models import AuditDetail, AuditTicket
from retailer_backend.admin import InputFilter


class SKUFilter(InputFilter):
    title = 'SKU'
    parameter_name = 'sku'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(sku=value)
        return queryset


class Warehouse(AutocompleteFilter):
    title = 'Warehouse'
    field_name = 'warehouse'
    autocomplete_url = 'warehouse-autocomplete'


class AssignedUserFilter(AutocompleteFilter):
    title = 'Assigned User'
    field_name = 'assigned_user'
    autocomplete_url = 'assigned-user-autocomplete'


@admin.register(AuditDetail)
class AuditDetailAdmin(admin.ModelAdmin):
    list_display = ('audit_type', 'audit_inventory_type', 'warehouse', 'status', 'user')
    fields = ('audit_type', 'audit_inventory_type', 'warehouse', 'status')
    list_filter = [Warehouse]
    form = AuditCreationForm
    actions_on_top = False

    class Media:
        pass


@admin.register(AuditTicket)
class AuditTicketAdmin(admin.ModelAdmin):
    list_display = ('audit_run_id', 'audit_type', 'audit_inventory_type',  'sku', 'batch_id', 'bin_id',
                    'inventory_type', 'inventory_state',
                    'qty_expected_type', 'qty_expected', 'qty_calculated_type', 'qty_calculated', 'created_at',
                    'status', 'assigned_user')

    fields = ['sku', 'batch_id', 'bin_id', 'qty_expected', 'qty_calculated',
              'created_at',  'updated_at',  'status', 'assigned_user']
    readonly_fields = ('sku', 'batch_id', 'bin_id', 'qty_expected', 'qty_calculated', 'created_at', 'updated_at')
    list_filter = [Warehouse, SKUFilter, AssignedUserFilter, 'status']
    date_hierarchy = 'created_at'
    actions_on_top = False

    class Media:
        pass



