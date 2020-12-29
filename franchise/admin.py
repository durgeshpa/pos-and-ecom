# Register your models here.
import csv
from django.contrib import admin
from django.db.models import Q
from rangefilter.filter import DateTimeRangeFilter
from django_admin_listfilter_dropdown.filters import DropdownFilter, ChoiceDropdownFilter
from django.http import HttpResponse

from franchise.models import Fbin, Faudit, HdposDataFetch, FranchiseSales, FranchiseReturns, ShopLocationMap
from franchise.forms import FranchiseBinForm, FranchiseAuditCreationForm, ShopLocationMapForm
from franchise.filters import ShopLocFilter, BarcodeFilter, ShopFilter, ShopLocFilter1, FranchiseShopAutocomplete
from wms.admin import BinAdmin, BinIdFilter
from audit.admin import AuditDetailAdmin, AuditNoFilter, AuditorFilter
from products.models import Product


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['created_at', 'modified_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            items= [getattr(obj, field) for field in field_names]
            writer.writerow(items)
        return response
    export_as_csv.short_description = "Download CSV of Selected Objects"


@admin.register(Fbin)
class FranchiseBinAdmin(BinAdmin):
    form = FranchiseBinForm

    list_filter = [BinIdFilter, ('created_at', DateTimeRangeFilter), ('modified_at', DateTimeRangeFilter),
                   ShopFilter, ('bin_type', DropdownFilter)]

    def get_urls(self):
        # To not overwrite existing url names for BinAdmin
        urls = super(BinAdmin, self).get_urls()
        return urls

    def get_queryset(self, request):
        qs = super(FranchiseBinAdmin, self).get_queryset(request)
        # Only Bins for shop type "Franchise" under B2C Franchise Management
        qs = qs.filter(warehouse__shop_type__shop_type='f')
        # Show bins for the logged in user warehouse/franchise only
        if not request.user.is_superuser:
            qs = qs.filter(Q(warehouse__related_users=request.user) | Q(warehouse__shop_owner=request.user))
        return qs

    # Default franchise virtual bin is created when franchise shop is approved. Other bins cannot be created.
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Faudit)
class FranchiseAuditAdmin(AuditDetailAdmin):
    form = FranchiseAuditCreationForm

    list_filter = [ShopFilter, AuditNoFilter, AuditorFilter, 'audit_run_type', 'audit_level', 'state', 'status']

    def get_urls(self):
        # To not overwrite existing url names for AuditDetailAdmin
        urls = super(AuditDetailAdmin, self).get_urls()
        return urls

    # custom template used for AuditDetailAdmin not required here
    change_list_template = 'admin/change_list.html'

    def get_queryset(self, request):
        qs = super(FranchiseAuditAdmin, self).get_queryset(request)
        # Only Audits for shop type "Franchise" under B2C Franchise Management
        qs = qs.filter(warehouse__shop_type__shop_type='f')
        # Show audits for the logged in user warehouse/franchise only
        if not request.user.is_superuser:
            qs = qs.filter(Q(warehouse__related_users=request.user) | Q(warehouse__shop_owner=request.user))
        return qs


@admin.register(HdposDataFetch)
class HdposDataFetchAdmin(admin.ModelAdmin):
    list_display = [field.name for field in HdposDataFetch._meta.get_fields()]
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FranchiseSales)
class FranchiseSalesAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ['id', 'shop_loc', 'shop_name', 'barcode', 'product_sku', 'quantity', 'amount', 'process_status',
                    'error', 'invoice_number', 'invoice_date', 'created_at', 'modified_at']
    list_per_page = 50
    actions = ["export_as_csv"]
    list_filter = [ShopLocFilter, BarcodeFilter, ('invoice_date', DateTimeRangeFilter), ('process_status', ChoiceDropdownFilter)]

    class Media:
        pass

    def shop_name(self, obj):
        return ShopLocationMap.objects.filter(location_name=obj.shop_loc).last().shop \
            if ShopLocationMap.objects.filter(location_name=obj.shop_loc).exists() else '-'

    def product_sku(self, obj):
        return Product.objects.filter(product_ean_code=obj.barcode).last().product_sku \
            if Product.objects.filter(product_ean_code=obj.barcode).count() == 1 else '-'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FranchiseReturns)
class FranchiseReturnsAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ['id', 'shop_loc', 'shop_name', 'barcode', 'product_sku', 'quantity', 'amount', 'process_status',
                    'error', 'sr_number', 'sr_date', 'created_at', 'modified_at']
    list_per_page = 50
    actions = ["export_as_csv"]
    list_filter = [ShopLocFilter, BarcodeFilter, ('sr_date', DateTimeRangeFilter), ('process_status', ChoiceDropdownFilter)]

    class Media:
        pass

    def shop_name(self, obj):
        return ShopLocationMap.objects.filter(location_name=obj.shop_loc).last().shop \
            if ShopLocationMap.objects.filter(location_name=obj.shop_loc).exists() else '-'

    def product_sku(self, obj):
        return Product.objects.filter(product_ean_code=obj.barcode).last().product_sku \
            if Product.objects.filter(product_ean_code=obj.barcode).count() == 1 else '-'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ShopLocationMap)
class ShopLocationMapAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = [field.name for field in ShopLocationMap._meta.get_fields()]
    list_per_page = 50
    list_filter = [ShopFilter, ShopLocFilter1]
    actions = ["export_as_csv"]
    form = ShopLocationMapForm

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ShopLocationMapAdmin, self).get_urls()
        urls = [
            url(
                r'^franchise-shop-autocomplete/$',
                self.admin_site.admin_view(FranchiseShopAutocomplete.as_view()),
                name="franchise-shop-autocomplete"
            ),
        ] + urls
        return urls

    class Media:
        pass

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False

    def has_change_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False

