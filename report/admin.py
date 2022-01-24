# -*- coding: utf-8 -*-

from django.contrib import admin

from report.models import AsyncReportRequest, ScheduledReport, ScheduledReportRequest


@admin.register(AsyncReportRequest)
class AsyncReportRequestAdmin(admin.ModelAdmin):

    list_filter = ('report_name', 'status', 'source')
    list_display = ('rid', 'report_name', 'status', 'user', 'created_at')
    readonly_fields = ('rid', 'report', 'created_at', 'updated_at', 
                       'report_created_at', 'user', 'status')
    fields = ('rid', 'report_name', 'report_type', 'source', 'input_params', 'emails',
              'report', 'status', 'user', 'report_created_at', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(report_type='AD')
    
    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

class ScheduledReportInlineAdmin(admin.TabularInline):
    
    model = ScheduledReport
    
    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ScheduledReportRequest)
class ScheduledReportRequestAdmin(admin.ModelAdmin):
    
    list_filter = ('report_name', 'status', 'source')
    list_display = ('rid', 'report_name', 'status', 'user', 'created_at')
    fields = ('rid', 'report_name', 'source', 'status', 'input_params',
              'user', 'frequency', 'schedule_time', 'report_created_at' ,
              'created_at', 'updated_at')
    readonly_fields = ('rid', 'report', 'created_at', 'updated_at', 
                       'report_created_at', 'user', 'status')
    inlines = [ScheduledReportInlineAdmin]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()
    
    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False