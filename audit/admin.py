import csv
import logging
from io import StringIO

from dal_admin_filters import AutocompleteFilter
from daterange_filter.filter import DateRangeFilter
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
from rangefilter.filter import DateRangeFilter

from audit.forms import AuditCreationForm, AuditTicketForm
from audit.models import AuditDetail, AuditTicket, AuditTicketManual, AUDIT_TICKET_STATUS_CHOICES
from retailer_backend.admin import InputFilter


info_logger = logging.getLogger('file-info')


class SKUFilter(InputFilter):
    title = 'SKU'
    parameter_name = 'sku'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(sku=value)
        return queryset


class AuditNoFilter(InputFilter):
    title = 'Audit No'
    parameter_name = 'id'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(id=value)
        return queryset

class Warehouse(AutocompleteFilter):
    title = 'Warehouse'
    field_name = 'warehouse'
    autocomplete_url = 'warehouse-autocomplete'


class AuditStateFilter(AutocompleteFilter):
    title = 'Audit State'
    field_name = 'state'
    autocomplete_url = 'audit-state-autocomplete'


class AssignedUserFilter(AutocompleteFilter):
    title = 'Assigned User'
    field_name = 'assigned_user'
    autocomplete_url = 'assigned-user-filter'


class AuditorFilter(AutocompleteFilter):
    title = 'Auditor'
    field_name = 'auditor'
    autocomplete_url = 'auditor-autocomplete'


@admin.register(AuditDetail)
class AuditDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'warehouse', 'audit_type', 'audit_inventory_type', 'audit_level',
                    'state', 'status', 'user', 'auditor', 'created_at')

    fieldsets = (
        ('Basic', {
            'fields': ('warehouse', 'audit_type', 'status'),
            'classes': ('required',)
        }),
        ('Automated Audit', {
            'fields': ('audit_inventory_type',),
            'classes': ('automated',)
        }),
        ('Manual Audit', {
            'fields': ('auditor', 'audit_level', 'bin', 'sku'),
            'classes': ('manual',)
        }),
    )
    list_filter = [Warehouse, AuditNoFilter, AuditorFilter, 'audit_type', 'audit_level', 'state', 'status']
    form = AuditCreationForm
    actions_on_top = False

    change_list_template = 'admin/audit/audit_ticket_change_list.html'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('warehouse', 'audit_type', 'audit_inventory_type', 'audit_level',
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

    readonly_fields = ('sku', 'batch_id', 'bin', 'qty_expected', 'qty_calculated', 'created_at', 'updated_at')
    list_filter = [Warehouse, SKUFilter, AssignedUserFilter, 'audit_run__audit__audit_type',
                   'audit_run__audit__audit_inventory_type', 'status', ('created_at', DateRangeFilter)]
    date_hierarchy = 'created_at'
    actions_on_top = False

    def audit_id(self, obj):
        return obj.audit_run.audit_id

    class Media:
        pass


@admin.register(AuditTicketManual)
class AuditTicketManualAdmin(admin.ModelAdmin):
    list_display = ('audit_id', 'bin', 'sku', 'batch_id', 'qty_normal_system', 'qty_normal_actual', 'normal_var',
                    'qty_damaged_system', 'qty_damaged_actual', 'damaged_var',
                    'qty_expired_system', 'qty_expired_actual', 'expired_var',
                    'total_var', 'status', 'assigned_user', 'created_at')

    list_filter = [Warehouse, SKUFilter, AssignedUserFilter, 'status']
    form = AuditTicketForm
    actions = ['download_tickets']

    def audit_id(self, obj):
        return obj.audit_run.audit_id

    def normal_var(self, obj):
        return obj.qty_normal_system - obj.qty_normal_actual

    def damaged_var(self, obj):
        return obj.qty_damaged_system - obj.qty_damaged_actual

    def expired_var(self, obj):
        return obj.qty_expired_system - obj.qty_expired_actual

    def total_var(self, obj):
        return obj.qty_normal_system + obj.qty_damaged_system + obj.qty_expired_system - \
               (obj.qty_damaged_actual + obj.qty_normal_actual + obj.qty_expired_actual)

    def download_tickets(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['audit_id', 'bin', 'sku', 'batch_id', 'qty_normal_system', 'qty_normal_actual', 'normal_var',
                         'qty_damaged_system', 'qty_damaged_actual', 'damaged_var',
                         'qty_expired_system', 'qty_expired_actual', 'expired_var',
                         'total_var', 'status'])

        for query in queryset:
            obj = AuditTicketManual.objects.get(id=query.id)
            writer.writerow([obj.audit_run.audit_id, obj.bin, obj.sku, obj.batch_id, obj.qty_normal_system,
                             obj.qty_normal_actual, self.normal_var(obj), obj.qty_damaged_system, obj.qty_damaged_actual,
                             self.damaged_var(obj), obj.qty_expired_system, obj.qty_expired_actual, self.expired_var(obj),
                             self.total_var(obj), AUDIT_TICKET_STATUS_CHOICES[obj.status]])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=manual-audit-tickets.csv'
        return response

    class Media:
        pass




