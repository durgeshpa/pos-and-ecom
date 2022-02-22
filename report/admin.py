# -*- coding: utf-8 -*-
from django.contrib import admin

from report.models import (AdHocReportRequest, 
                           ScheduledReport, 
                           ScheduledReportRequest, 
                           ReportChoice)

@admin.register(ReportChoice)
class ReportChoiceAdmin(admin.ModelAdmin):
    list_filter = ('is_active', 'target_model', 'source')
    list_display = ('name', 'target_model', 'source','is_active', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    

@admin.register(AdHocReportRequest)
class AdHocReportRequestAdmin(admin.ModelAdmin):

    list_filter = ('status',)
    list_display = ('rid', 'report_choice', 'status', 'user', 'created_at', 'report_created_at')
    readonly_fields = ('rid', 'report', 'created_at', 'updated_at', 
                       'report_created_at', 'user', 'status', 'failed_message')
    fields = ('rid', 'report_choice', 'input_params', 'emails', 'failed_message',
              'report', 'status', 'user', 'report_created_at', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()
    
    # def has_delete_permission(self, request, obj=None):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_add_permission(self, request, obj=None):
    #     return False

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
    
    list_filter = ('status', 'frequency')
    list_display = ('rid', 'report_choice', 'status', 'user', 'created_at')
    fields = ('rid', 'report_choice', 'input_params', 'failed_message',
              'user', 'frequency', 'schedule_time', 
              'status','report_created_at' ,
              'created_at', 'updated_at')
    readonly_fields = ('rid', 'report', 'created_at', 'updated_at', 'failed_message',
                       'report_created_at', 'user', 'status')
    inlines = [ScheduledReportInlineAdmin]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()
    
    # def has_delete_permission(self, request, obj=None):
    #     return True

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_add_permission(self, request, obj=None):
    #     return False