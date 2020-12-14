# Register your models here.

from django.contrib import admin
from django.db.models import Q

from franchise.models import Fbin, Faudit
from franchise.forms import FranchiseBinForm, FranchiseAuditCreationForm
from wms.admin import BinAdmin
from audit.admin import AuditDetailAdmin


@admin.register(Fbin)
class FranchiseBinAdmin(BinAdmin):
    form = FranchiseBinForm

    def get_queryset(self, request):
        qs = super(FranchiseBinAdmin, self).get_queryset(request)
        qs = qs.filter(warehouse__shop_type__shop_type='f')
        if not request.user.is_superuser:
            qs = qs.filter(Q(warehouse__related_users=request.user) | Q(warehouse__shop_owner=request.user))
        return qs


@admin.register(Faudit)
class FranchiseAuditAdmin(AuditDetailAdmin):
    form = FranchiseAuditCreationForm

    def get_queryset(self, request):
        qs = super(FranchiseAuditAdmin, self).get_queryset(request)
        qs = qs.filter(warehouse__shop_type__shop_type='f')
        if not request.user.is_superuser:
            qs = qs.filter(Q(warehouse__related_users=request.user) | Q(warehouse__shop_owner=request.user))
        return qs
