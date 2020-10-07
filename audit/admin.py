import logging

from dal_admin_filters import AutocompleteFilter
from daterange_filter.filter import DateRangeFilter
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
    list_display = ('id', 'warehouse', 'audit_type', 'audit_inventory_type', 'audit_level', 'state', 'status', 'user', 'auditor')

    fieldsets = (
        ('Basic', {
            'fields': ('warehouse', 'audit_type','status'),
            'classes': ('required',)
        }),
        ('Automated Audit', {
            'fields': ('audit_inventory_type',),
            'classes': ('automated',)
        }),
        ('Manual Audit', {
            'fields': ('auditor', 'audit_level', 'bin', 'sku', ),
            'classes': ('manual',)
        }),
    )
    list_filter = [Warehouse, 'audit_type']
    form = AuditCreationForm
    actions_on_top = False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ( 'warehouse', 'audit_type', 'audit_inventory_type', 'audit_level',
                                            'bin', 'sku', 'user', 'auditor')
        return self.readonly_fields

    class Media:
        js = ("admin/js/audit_admin_form.js",)


@admin.register(AuditTicket)
class AuditTicketAdmin(admin.ModelAdmin):
    list_display = ('audit_id', 'audit_run_id', 'audit_type', 'audit_inventory_type',  'sku_id', 'batch_id', 'bin',
                    'inventory_type', 'inventory_state',
                    'qty_expected_type', 'qty_expected', 'qty_calculated_type', 'qty_calculated', 'created_at',
                    'status', 'assigned_user')

    fields = ['sku_id', 'batch_id', 'bin', 'qty_expected', 'qty_calculated',
              'created_at',  'updated_at',  'status', 'assigned_user']
    readonly_fields = ('sku', 'batch_id', 'bin_id', 'qty_expected', 'qty_calculated', 'created_at', 'updated_at')
    list_filter = [Warehouse, SKUFilter, AssignedUserFilter, 'status', ('created_at', DateRangeFilter)]
    date_hierarchy = 'created_at'
    actions_on_top = False

    def audit_id(self, obj):
        return obj.audit_run.audit_id

    class Media:
        pass



