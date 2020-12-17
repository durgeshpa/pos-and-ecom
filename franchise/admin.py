# Register your models here.

from django.contrib import admin
from django.db.models import Q
from rangefilter.filter import DateTimeRangeFilter
from django_admin_listfilter_dropdown.filters import DropdownFilter

from franchise.models import Fbin, Faudit
from franchise.forms import FranchiseBinForm, FranchiseAuditCreationForm
from wms.admin import BinAdmin, BinIdFilter
from audit.admin import AuditDetailAdmin, AuditNoFilter, AuditorFilter


@admin.register(Fbin)
class FranchiseBinAdmin(BinAdmin):
    form = FranchiseBinForm

    list_filter = [BinIdFilter, ('created_at', DateTimeRangeFilter), ('modified_at', DateTimeRangeFilter),
                   ('bin_type', DropdownFilter)]

    def get_urls(self):
        urls = super(BinAdmin, self).get_urls()
        return urls

    def get_queryset(self, request):
        qs = super(FranchiseBinAdmin, self).get_queryset(request)
        qs = qs.filter(warehouse__shop_type__shop_type='f')
        if not request.user.is_superuser:
            qs = qs.filter(Q(warehouse__related_users=request.user) | Q(warehouse__shop_owner=request.user))
        return qs

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Faudit)
class FranchiseAuditAdmin(AuditDetailAdmin):
    form = FranchiseAuditCreationForm

    list_filter = [AuditNoFilter, AuditorFilter, 'audit_run_type', 'audit_level', 'state', 'status']

    def get_urls(self):
        urls = super(AuditDetailAdmin, self).get_urls()
        return urls

    change_list_template = 'admin/change_list.html'

    def get_queryset(self, request):
        qs = super(FranchiseAuditAdmin, self).get_queryset(request)
        qs = qs.filter(warehouse__shop_type__shop_type='f')
        if not request.user.is_superuser:
            qs = qs.filter(Q(warehouse__related_users=request.user) | Q(warehouse__shop_owner=request.user))
        return qs
