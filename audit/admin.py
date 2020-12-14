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

from .views import bulk_audit_csv_upload_view,AuditDownloadSampleCSV
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
    parameter_name = 'audit_no'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(audit_no=value)
        return queryset


class AuditNoFilterForTickets(InputFilter):
    title = 'Audit No'
    parameter_name = 'audit_no'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(audit_run__audit__audit_no=value)
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

class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"

@admin.register(AuditDetail)
class AuditDetailAdmin(admin.ModelAdmin,ExportCsvMixin):
    list_display = ('audit_no', 'warehouse', 'audit_run_type', 'audit_inventory_type', 'audit_level',
                    'state', 'status', 'user', 'auditor', 'created_at')

    fieldsets = (
        ('Basic', {
            'fields': ('warehouse', 'audit_run_type', 'status'),
            'classes': ('required',)
        }),
        ('Automated Audit', {
            'fields': ('audit_inventory_type', 'is_historic', 'audit_from'),
            'classes': ('automated',)
        }),
        ('Manual Audit', {
            'fields': ('auditor', 'audit_level', 'bin', 'sku'),
            'classes': ('manual',)
        }),
    )
    list_filter = [Warehouse, AuditNoFilter, AuditorFilter, 'audit_run_type', 'audit_level', 'state', 'status']
    form = AuditCreationForm
    # actions_on_top = False
    actions = ['export_as_csv']
   
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['auditrun','updated_at','id','audit_from']
        fields = [field for field in meta.get_fields() if field.name not in exclude_fields]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow([field.name.title() for field in fields])
        for obj in queryset:
          
            row = []
          
            for field in fields:
        
                if field.many_to_many == True or field.one_to_many == True:
                    try:
                        if field.name == "bin":
                            val = list(getattr(obj,field.name).all().values_list('bin_id', flat=True))
                        elif field.name == "sku":
                            val = list(getattr(obj,field.name).all().values_list('product_sku', flat=True))
                    except:
                        val = str(obj).replace(";", "")
                else:
                    val = str(getattr(obj, field.name)).replace(";", "")
              
                row.append(val)
            writer.writerow(row)
        return response
    export_as_csv.short_description = "Download CSV for selected Audit Tasks"
 

    change_list_template = 'admin/audit/audit_ticket_change_list.html'
   
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('warehouse', 'audit_run_type', 'audit_inventory_type', 'audit_level',
                                           'bin', 'sku', 'user', 'auditor', 'is_historic', 'audit_from')
        return self.readonly_fields

    class Media:
        js = ("admin/js/audit_admin_form.js",)
    
    def get_urls(self):
        from django.conf.urls import url
        urls = super(AuditDetailAdmin, self).get_urls()
        urls = [
            url(
                r'^audit-csv-upload/$',
                self.admin_site.admin_view(bulk_audit_csv_upload_view),
                name="audit-csv-upload"
            ),
            url(
                r'^audit-csv-sample/$',
                self.admin_site.admin_view(AuditDownloadSampleCSV),
                name="audit-csv-sample"
            ),
           
        ] + urls
        return urls


@admin.register(AuditTicket)
class AuditTicketAdmin(admin.ModelAdmin):
    list_display = ('audit_id', 'audit_run_id', 'audit_run_type', 'audit_inventory_type',  'sku_id', 'batch_id', 'bin',
                    'inventory_type', 'inventory_state',
                    'qty_expected_type', 'qty_expected', 'qty_calculated_type', 'qty_calculated', 'created_at',
                    'status', 'assigned_user')

    readonly_fields = ('sku', 'batch_id', 'bin', 'qty_expected', 'qty_calculated', 'created_at', 'updated_at')
    list_filter = [Warehouse, SKUFilter, AssignedUserFilter, 'audit_run__audit__audit_run_type',
                   'audit_run__audit__audit_inventory_type', 'status', ('created_at', DateRangeFilter)]
    date_hierarchy = 'created_at'
    actions_on_top = False

    def audit_id(self, obj):
        return obj.audit_run.audit_id

    class Media:
        pass

@admin.register(AuditTicketManual)
class AuditTicketManualAdmin(admin.ModelAdmin):
    list_display = ('audit_no', 'bin', 'sku', 'batch_id', 'qty_normal_system', 'qty_normal_actual', 'normal_var',
                    'qty_damaged_system', 'qty_damaged_actual', 'damaged_var',
                    'qty_expired_system', 'qty_expired_actual', 'expired_var',
                    'total_var', 'status', 'assigned_user', 'created_at')

    list_filter = [Warehouse, AuditNoFilterForTickets, SKUFilter, AssignedUserFilter, 'status',  ('created_at', DateRangeFilter)]
    form = AuditTicketForm
    actions = ['download_tickets']

    def audit_id(self, obj):
        return obj.audit_run.audit_id

    def audit_no(self, obj):
        return obj.audit_run.audit.audit_no

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
