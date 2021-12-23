# -*- coding: utf-8 -*-

from django.contrib import admin

from report.models import AsyncReport


@admin.register(AsyncReport)
class AsyncReport(admin.ModelAdmin):

    list_filter = ('report_name', 'report_type', 'status')
    list_display = ('rid', 'report_name', 'report_type', 'status', 'user', 'created_at')
    readonly_fields = ('rid', 'report', 'created_at', 'updated_at', 'report_created_at', 'user')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()
    
    def has_delete_permission(self, request, obj=None):
        return False
