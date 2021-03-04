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

from audit.models import AuditDetail, AuditTicket, AuditTicketManual, AUDIT_DETAIL_STATUS_CHOICES, \
    AUDIT_DETAIL_STATE_CHOICES, AUDIT_RUN_STATUS_CHOICES, AUDIT_TICKET_STATUS_CHOICES, AUDIT_INVENTORY_CHOICES, \
    AUDIT_RUN_TYPE_CHOICES, AUDIT_LEVEL_CHOICES, AuditRun
from retailer_backend.admin import InputFilter
from retailer_backend.utils import time_diff_days_hours_mins_secs
from wms.models import Bin
from .utils import get_audit_start_time, get_audit_complete_time, get_audit_completion_time_string
from .views import bulk_audit_csv_upload_view,AuditDownloadSampleCSV
from audit.models import AuditDetail, AuditTicket, AuditTicketManual, AUDIT_TICKET_STATUS_CHOICES, \
    AuditCancelledPicklist, AuditProduct, AUDIT_LEVEL_CHOICES, AUDIT_DETAIL_STATE_CHOICES, AUDIT_DETAIL_STATUS_CHOICES
from products.models import Product
from retailer_backend.admin import InputFilter
from retailer_to_sp.models import CartProductMapping
info_logger = logging.getLogger('file-info')
import traceback

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


class AuditNoFilterForCancelledPicklists(InputFilter):
    title = 'Audit No'
    parameter_name = 'audit_no'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(audit__audit_no=value)
        return queryset

class OrderNoFilter(InputFilter):
    title = 'Order No'
    parameter_name = 'order_no'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(order_no=value)
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
                    'state', 'status', 'user', 'auditor', 'created_at', 'started_at', 'completed_at', 'completion_time')

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
            'fields': ('auditor', 'audit_level', 'bin', 'sku', 'pbi'),
            'classes': ('manual',)
        }),
    )
    list_filter = [Warehouse, AuditNoFilter, AuditorFilter, 'audit_run_type', 'audit_level', 'state', 'status']
    form = AuditCreationForm
    actions = ['export_as_csv']

    def audit_level(self, obj):
        audit_level = ""
        if obj.audit_level is not None:
            audit_level = AUDIT_LEVEL_CHOICES[obj.audit_level]
            return audit_level
        else:
            return audit_level

    def started_at(self, obj):
        return get_audit_start_time(obj)

    def completed_at(self, obj):
        return get_audit_complete_time(obj)

    def completion_time(self, obj):
        return get_audit_completion_time_string(obj)

    def export_as_csv(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['audit_no','warehouse','audit_run_type','audit_level','state',
                        'status','created_by','auditor','created_at','bin','sku', 'started_at', 'completed_at',
                         'completion_time'])
    
        queryset = queryset.filter(audit_run_type = AUDIT_RUN_TYPE_CHOICES.MANUAL )
        for query in queryset:
            
            obj = AuditDetail.objects.get(id=query.id)
            try:
                writer.writerow([obj.audit_no,obj.warehouse,AUDIT_RUN_TYPE_CHOICES[obj.audit_run_type],
                self.audit_level(obj),AUDIT_DETAIL_STATE_CHOICES[obj.state],
                AUDIT_DETAIL_STATUS_CHOICES[obj.status],obj.user,obj.auditor,obj.created_at,
                list(getattr(obj,"bin").all().values_list('bin_id', flat=True)),
                list(getattr(obj,"sku").all().values_list('product_sku', flat=True)),
                self.started_at(obj), self.completed_at(obj), self.completion_time(obj)])

            except Exception as exc:
                trace_back = traceback.format_exc()
                message = str(exc)+ " " + str(trace_back)
                print(message)

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=auditDetails.csv'
        return response
        
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
                    'total_var', 'status', 'assigned_user', 'created_at', 'audit_completion_time')

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

    def audit_completion_time(self, obj):
        return time_diff_days_hours_mins_secs(obj.audit_run.completed_at, obj.audit_run.created_at)

    def download_tickets(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['audit_id', 'bin', 'sku', 'batch_id', 'audit_task_number',
                         'warehouse_name', 'audit_type', 'audit_state', 'auditor', 'created_at',
                         'qty_normal_system', 'qty_normal_actual', 'normal_var',
                         'qty_damaged_system', 'qty_damaged_actual', 'damaged_var',
                         'qty_expired_system', 'qty_expired_actual', 'expired_var',
                         'total_var', 'status', 'audit_completion_time'])

        for query in queryset:
            obj = AuditTicketManual.objects.get(id=query.id)
            writer.writerow([obj.audit_run.audit_id, obj.bin, obj.sku, obj.batch_id, obj.audit_run.audit.audit_no,
                             obj.warehouse, AUDIT_LEVEL_CHOICES[obj.audit_run.audit.audit_level],
                             AUDIT_DETAIL_STATE_CHOICES[obj.audit_run.audit.state], obj.audit_run.audit.auditor,
                             obj.created_at, obj.qty_normal_system, obj.qty_normal_actual, self.normal_var(obj),
                             obj.qty_damaged_system, obj.qty_damaged_actual, self.damaged_var(obj),
                             obj.qty_expired_system, obj.qty_expired_actual, self.expired_var(obj),
                             self.total_var(obj), AUDIT_TICKET_STATUS_CHOICES[obj.status],
                             self.audit_completion_time(obj)])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=manual-audit-tickets.csv'
        return response

    class Media:
        pass
@admin.register(AuditCancelledPicklist)
class AuditCancelledPicklistAdmin(admin.ModelAdmin):
    list_display = ('audit_no', 'audit_state', 'audit_status', 'order_no', 'is_picklist_refreshed', 'audit_skus', 'created_at')
    list_filter = [OrderNoFilter, AuditNoFilterForCancelledPicklists, 'is_picklist_refreshed',  ('created_at', DateRangeFilter)]
    actions = ['download_csv']

    def audit_no(self, obj):
        return obj.audit.audit_no

    def audit_state(self, obj):
        return AUDIT_DETAIL_STATE_CHOICES[obj.audit.state]

    def audit_status(self, obj):
        return AUDIT_DETAIL_STATUS_CHOICES[obj.audit.status]

    def audit_skus(self, obj):
        audit_skus = AuditProduct.objects.filter(audit=obj.audit).values_list('sku_id', flat=True)
        product_ids = Product.objects.only('id').filter(product_sku__in=audit_skus)
        cart_products = CartProductMapping.objects.filter(cart__order_id=obj.order_no,
                                                          cart_product_id__in=product_ids)\
                                                  .values_list('cart_product__product_sku', flat=True)
        return list(cart_products)

    def download_csv(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(['Audit No', 'Audit State', 'Audit Status', 'Order No', 'Picklist Refreshed', 'SKUs',
                         'Cancelled At'])

        for query in queryset:
            obj = AuditCancelledPicklist.objects.get(id=query.id)
            writer.writerow([obj.audit.audit_no, self.audit_state(obj), self.audit_status(obj), obj.order_no,
                             obj.is_picklist_refreshed, self.audit_skus(obj), obj.created_at])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=audit-cancelled-picklist.csv'
        return response

    class Media:
        pass

