# python imports
import logging
import csv
import datetime
from io import StringIO
from dal_admin_filters import AutocompleteFilter
# django imports
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django_admin_listfilter_dropdown.filters import ChoiceDropdownFilter, DropdownFilter
from rangefilter.filter import DateTimeRangeFilter

from products.models import ProductVendorMapping
from retailer_backend.admin import InputFilter
# app imports
from .views import bins_upload, put_away, CreatePickList, audit_download, audit_upload
from import_export import resources
from .models import (Bin, InventoryType, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup,
                     PickupBinInventory,
                     WarehouseInventory, InventoryState, WarehouseInternalInventoryChange, StockMovementCSVUpload,
                     BinInternalInventoryChange, StockCorrectionChange, OrderReserveRelease, Audit)
from .forms import (BinForm, InForm, PutAwayForm, PutAwayBinInventoryForm, BinInventoryForm, OutForm, PickupForm,
                    StockMovementCSVUploadAdminForm)
from barCodeGenerator import barcodeGen, merged_barcode_gen
from gram_to_brand.models import GRNOrderProductMapping

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BinResource(resources.ModelResource):
    info_logger.info("Bin Resource Admin has been called.")

    class Meta:
        model = Bin
        exclude = ('created_at', 'modified_at')


class BinIdFilter(InputFilter):
    title = 'Bin ID'
    parameter_name = 'bin_id'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(bin_id=value)
        return queryset


class BinIDFilterForPickupBinInventory(InputFilter):
    title = 'Bin ID'
    parameter_name = 'bin'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(bin__bin__bin_id=value)
        return queryset


class BinIDFilterForBinInventory(InputFilter):
    title = 'Bin ID'
    parameter_name = 'bin'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(bin__bin_id=value)
        return queryset


class BatchIdFilter(InputFilter):
    title = 'Batch ID'
    parameter_name = 'batch_id'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(batch_id=value)
        return queryset


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


class InventoryTypeFilter(AutocompleteFilter):
    title = 'Inventory Type'
    field_name = 'inventory_type'
    autocomplete_url = 'inventory-type-autocomplete'


class InventoryStateFilter(AutocompleteFilter):
    title = 'Inventory State'
    field_name = 'inventory_state'
    autocomplete_url = 'inventory-state-autocomplete'


class InitialStageFilter(AutocompleteFilter):
    title = 'Initial Stage'
    field_name = 'initial_stage'
    autocomplete_url = 'initial-stage-autocomplete'


class FinalStageFilter(AutocompleteFilter):
    title = 'Final Stage'
    field_name = 'final_stage'
    autocomplete_url = 'final-stage-autocomplete'


class InTypeIDFilter(InputFilter):
    title = 'In Type ID'
    parameter_name = 'in_type_id'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(in_type_id=value)
        return queryset


class PicktypeIDFilter(InputFilter):
    title = 'Pickup Type ID'
    parameter_name = 'pickup_type_id'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(pickup_type_id=value)
        return queryset


class TransactionIDFilter(InputFilter):
    title = 'Transaction ID'
    parameter_name = 'transaction_id'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(transaction_id=value)
        return queryset


class OutTypeIDFilter(InputFilter):
    title = 'OUT TYPE ID'
    parameter_name = 'out_type_id'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(out_type_id=value)
        return queryset


class ProductSKUFilter(InputFilter):
    title = 'SKU'
    parameter_name = 'sku'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(sku__product_sku=value)
        return queryset


class PutawayuserFilter(AutocompleteFilter):
    title = 'PUTAWAY USER'
    field_name = 'putaway_user'
    autocomplete_url = 'putaway-user-autocomplete'


class BinAdmin(admin.ModelAdmin):
    info_logger.info("Bin Admin has been called.")
    form = BinForm
    resource_class = BinResource
    actions = ['download_csv_for_bins', 'download_barcode']
    list_display = (
        'warehouse', 'bin_id', 'bin_type', 'created_at', 'modified_at', 'is_active','bin_barcode_txt', 'download_bin_id_barcode')
    # readonly_fields = ['warehouse', 'bin_id', 'bin_type', 'bin_barcode', 'barcode_image',
    #                    'download_bin_id_barcode', 'download_barcode_image']
    search_fields = ('bin_id',)
    list_filter = [BinIdFilter,
                   ('created_at', DateTimeRangeFilter), ('modified_at', DateTimeRangeFilter), Warehouse,
                   ('bin_type', DropdownFilter),
                   ]
    list_per_page = 50

    class Media:
        js = ('admin/js/picker.js',)

    def get_urls(self):
        from django.conf.urls import url
        urls = super(BinAdmin, self).get_urls()
        urls = [
                   url(
                       r'^upload-csv/$',
                       self.admin_site.admin_view(bins_upload),
                       name="bins-upload"
                   ),
                   url(
                       r'^putaway/$',
                       self.admin_site.admin_view(put_away),
                       name="putaway-bins"
                   )
               ] + urls
        return urls

    def download_bin_id_barcode(self, obj):
        id = getattr(obj, "id")
        return format_html(
            "<a href= '%s' >Download Barcode</a>" %
            (reverse('merged_barcodes', args=[id]))
        )

    download_bin_id_barcode.short_description = 'Download Bin ID Barcode'

    def download_csv_for_bins(self, request, queryset):
        """
        :param self:
        :param request:
        :param queryset:
        :return:
        """
        info_logger.info("download csv for bin method has been called.")
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response

    def download_barcode(self, request, queryset):
        """
        :param self:
        :param request:
        :param queryset:
        :return:
        """
        info_logger.info("download Barocde List for bin method has been called.")
        bin_id_list = {}
        for obj in queryset:
            bin_barcode_txt = getattr(obj, "bin_barcode_txt")
            if bin_barcode_txt is None:
                bin_barcode_txt = '1' + str(getattr(obj, 'id')).zfill(11)
            bin_id_list[bin_barcode_txt] = {"qty": 1, "data": {"Bin":getattr(obj, 'bin_id')}}
        return merged_barcode_gen(bin_id_list)

    download_csv_for_bins.short_description = "Download CSV of selected bins"
    download_barcode.short_description = "Download Barcode List"


class InAdmin(admin.ModelAdmin):
    info_logger.info("In Admin has been called.")
    form = InForm
    list_display = ('id', 'warehouse', 'sku', 'batch_id', 'in_type', 'in_type_id', 'quantity',)
    readonly_fields = ('warehouse', 'in_type', 'in_type_id', 'sku', 'batch_id', 'quantity',)
    search_fields = ('batch_id', 'in_type_id', 'sku__product_sku',)
    list_filter = [Warehouse, BatchIdFilter, SKUFilter, InTypeIDFilter, 'in_type']
    list_per_page = 50

    class Media:
        pass


class PutAwayAdmin(admin.ModelAdmin):
    info_logger.info("Put Away Admin has been called.")
    form = PutAwayForm
    list_display = (
        'putaway_user', 'warehouse', 'putaway_type', 'putaway_type_id', 'sku', 'batch_id', 'quantity',
        'putaway_quantity')
    readonly_fields = (
    'warehouse', 'putaway_type', 'putaway_type_id', 'sku', 'batch_id', 'quantity', 'putaway_quantity',)
    search_fields = ('putaway_user__phone_number', 'batch_id', 'sku__product_sku',)
    list_filter = [Warehouse, BatchIdFilter, SKUFilter, ('putaway_type', DropdownFilter), PutawayuserFilter]
    list_per_page = 50

    class Media:
        pass

class PutawayBinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Put Away Bin Inventory Admin has been called.")
    form = PutAwayBinInventoryForm
    list_display = ('warehouse', 'sku', 'batch_id', 'putaway_type', 'putaway_id', 'bin_id', 'putaway_quantity',
                    'putaway_status', 'created_at')
    actions = ['download_bulk_put_away_bin_inventory_csv']
    readonly_fields = ['warehouse', 'sku', 'batch_id', 'putaway_type', 'putaway','putaway_quantity']
    search_fields = ('batch_id', 'sku__product_sku', 'bin__bin__bin_id')
    list_filter = [
        Warehouse, BatchIdFilter, SKUFilter, BinIdFilter, ('putaway_type', DropdownFilter),
        ('created_at', DateTimeRangeFilter)]
    list_per_page = 50

    def download_bulk_put_away_bin_inventory_csv(self, request, queryset):
        """

        :param request: get request
        :param queryset: Put Away BinInventory queryset
        :return: csv file
        """
        f = StringIO()
        writer = csv.writer(f)
        # set the header name
        writer.writerow(["Warehouse", "SKU", "Batch ID ",
                         "Put Away Type", "Put Away ID", "Bin ID", "Put Away Quantity", "Put Away Status"])

        for query in queryset:
            # iteration for selected id from Admin Dashboard and get the instance
            putaway_bin_inventory = PutawayBinInventory.objects.get(id=query.id)
            # get object from queryset
            writer.writerow([putaway_bin_inventory.warehouse_id,
                             putaway_bin_inventory.sku.product_name + '-' + putaway_bin_inventory.sku.product_sku,
                             putaway_bin_inventory.batch_id, putaway_bin_inventory.putaway_type,
                             putaway_bin_inventory.putaway_id,
                             putaway_bin_inventory.bin_id,
                             putaway_bin_inventory.putaway_quantity,
                             putaway_bin_inventory.putaway_status])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=putaway_bin_inventory_download.csv'
        return response

    def putaway_id(self, obj):
        return obj.putaway_id

    def bin_id(self, obj):
        try:
            if obj is None:
                pass
            return obj.bin.bin.bin_id
        except:
            pass

    putaway_id.short_description = 'Putaway ID'
    bin_id.short_description = 'Bin Id'

    # download bulk invoice short description
    download_bulk_put_away_bin_inventory_csv.short_description = "Download Bulk Data in CSV"

    class Media:
        css = {"all": ("admin/css/disable_save_and_continue_editing_button.css",)}

    def get_form(self, request, obj=None, **kwargs):
        ModelForm = super(PutawayBinInventoryAdmin, self).get_form(request, obj, **kwargs)
        class ModelFormWithRequest(ModelForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return ModelForm(*args, **kwargs)
        return ModelFormWithRequest


class InventoryTypeAdmin(admin.ModelAdmin):
    info_logger.info("Inventory Type Admin has been called.")
    list_display = ('inventory_type',)
    list_per_page = 50


class BinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Bin Inventory Admin has been called.")
    form = BinInventoryForm
    actions = ['download_barcode']
    list_display = (
    'batch_id', 'warehouse', 'sku', 'bin', 'inventory_type', 'quantity', 'in_stock', 'created_at', 'modified_at')
    readonly_fields = ['warehouse', 'bin', 'sku', 'batch_id', 'inventory_type', 'quantity', 'in_stock']
    search_fields = ('batch_id', 'sku__product_sku', 'bin__bin_id', 'created_at', 'modified_at')
    list_filter = [BinIDFilterForBinInventory, Warehouse, BatchIdFilter, SKUFilter, InventoryTypeFilter]
    list_per_page = 50

    class Media:
        js = ('admin/js/picker.js',)

    def download_barcode(self, request, queryset):
        """
        :param self:
        :param request:
        :param queryset:
        :return:
        """
        info_logger.info("download Barocde List for GRN method has been called.")
        bin_id_list = {}
        for obj in queryset:
            product_mrp = ProductVendorMapping.objects.filter(product=obj.sku).last()

            temp_data = {"qty": 1, "data": {"SKU": obj.sku.product_name,
                                            "MRP": product_mrp.product_mrp if product_mrp.product_mrp else ''}}
            product_id = str(obj.sku.id).zfill(5)
            barcode_id = str("2" + product_id + str(obj.batch_id[-6:]))
            bin_id_list[barcode_id] = temp_data
        return merged_barcode_gen(bin_id_list)

    download_barcode.short_description = "Download Barcode List"


class OutAdmin(admin.ModelAdmin):
    info_logger.info("Out Admin has been called.")
    form = OutForm
    list_display = ('warehouse', 'out_type', 'out_type_id', 'sku', 'batch_id', 'quantity', 'created_at', 'modified_at')
    readonly_fields = (
    'warehouse', 'out_type', 'out_type_id', 'sku', 'batch_id', 'quantity', 'created_at', 'modified_at')
    list_filter = [Warehouse, ('out_type', DropdownFilter), SKUFilter, BatchIdFilter, OutTypeIDFilter]
    list_per_page = 50

    class Media:
        pass

    def get_urls(self):
        from django.conf.urls import url
        urls = super(OutAdmin, self).get_urls()
        urls = [
                   url(
                       r'^create-pick-list/(?P<pk>\d+)/picklist/$', CreatePickList.as_view(), name='create-picklist'
                   )
               ] + urls
        return urls


class PickupAdmin(admin.ModelAdmin):
    info_logger.info("Pick up Admin has been called.")
    form = PickupForm
    list_display = ('warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'quantity', 'pickup_quantity', 'status')
    readonly_fields = (
    'warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'quantity', 'pickup_quantity', 'status', 'out',)
    search_fields = ('pickup_type_id', 'sku__product_sku',)
    list_filter = [Warehouse, PicktypeIDFilter, SKUFilter, ('status', DropdownFilter), 'pickup_type']
    list_per_page = 50

    class Media:
        pass


class PickupBinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Pick up Bin Inventory Admin has been called.")

    list_display = ('warehouse', 'batch_id', 'order_number', 'bin_id', 'quantity', 'pickup_quantity', 'created_at')
    list_select_related = ('warehouse', 'pickup', 'bin')
    readonly_fields = ('quantity', 'pickup_quantity', 'warehouse', 'pickup', 'batch_id', 'bin', 'created_at')
    search_fields = ('batch_id', 'bin__bin__bin_id')
    list_filter = [Warehouse, BatchIdFilter, BinIDFilterForPickupBinInventory, ('created_at', DateTimeRangeFilter)]
    list_per_page = 50

    def order_number(self, obj):
        return obj.pickup.pickup_type_id

    def bin_id(self, obj):
        return obj.bin.bin.bin_id

    class Media:
        pass

    order_number.short_description = 'Order Number'
    bin_id.short_description = 'Bin Id'


class StockMovementCSVUploadAdmin(admin.ModelAdmin):
    """
    This class is used to view the Stock(Movement) form Admin Panel
    """
    form = StockMovementCSVUploadAdminForm
    list_display = ('id', 'uploaded_by', 'created_at', 'upload_csv')
    list_display_links = None
    list_per_page = 50

    def render_change_form(self, request, context, *args, **kwargs):
        """

        :param request: request
        :param context: context processor
        :param args: non keyword argument
        :param kwargs: keyword argument
        :return: Stock Movement Admin form
        """
        self.change_form_template = 'admin/wms/stock_movement_change_from.html'
        return super(StockMovementCSVUploadAdmin, self).render_change_form(request, context, *args, **kwargs)

    def get_form(self, request, *args, **kwargs):
        """

        :param request: request
        :param args: non keyword argument
        :param kwargs: keyword argument
        :return: form
        """
        form = super(StockMovementCSVUploadAdmin, self).get_form(request, *args, **kwargs)
        form.current_user = request.user
        return form

    def get_queryset(self, request):
        """

        :param request: get request
        :return: queryset
        """
        qs = super(StockMovementCSVUploadAdmin, self).get_queryset(request)
        return qs


class WarehouseInventoryAdmin(admin.ModelAdmin):
    list_display = (
        'warehouse', 'sku', 'inventory_type', 'inventory_state', 'quantity', 'in_stock', 'created_at', 'modified_at')
    list_select_related = ('warehouse', 'inventory_type', 'inventory_state', 'sku')

    readonly_fields = (
    'warehouse', 'sku', 'inventory_type', 'inventory_state', 'in_stock', 'created_at', 'modified_at', 'quantity',)
    search_fields = ('sku__product_sku',)
    list_filter = [Warehouse, SKUFilter, InventoryTypeFilter, InventoryStateFilter, ('created_at', DateTimeRangeFilter),
                   ('modified_at', DateTimeRangeFilter)]
    list_per_page = 50

    class Media:
        pass


class InventoryStateAdmin(admin.ModelAdmin):
    list_display = ('inventory_state',)
    list_per_page = 50


class WarehouseInternalInventoryChangeAdmin(admin.ModelAdmin):
    list_display = (
        'warehouse', 'sku', 'transaction_type', 'transaction_id', 'initial_type', 'initial_stage',
        'final_type', 'final_stage', 'quantity', 'created_at', 'modified_at', 'inventory_csv')
    list_select_related = ('warehouse', 'sku')
    readonly_fields = (
        'inventory_type', 'inventory_csv', 'status', 'warehouse', 'sku', 'transaction_type', 'transaction_id',
        'initial_type', 'initial_stage',
        'final_type', 'final_stage', 'quantity', 'created_at', 'modified_at')

    search_fields = ('sku__product_sku', 'transaction_id',)
    list_filter = [Warehouse, ProductSKUFilter, TransactionIDFilter, InventoryTypeFilter, InitialStageFilter,
                   FinalStageFilter, ('transaction_type', DropdownFilter), ('created_at', DateTimeRangeFilter),
                   ('modified_at', DateTimeRangeFilter)]
    list_per_page = 50

    class Media:
        pass


class BinInternalInventoryChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'batch_id', 'initial_inventory_type', 'final_inventory_type', 'initial_bin',
                    'final_bin', 'transaction_type', 'transaction_id',
                    'quantity', 'created_at', 'modified_at', 'inventory_csv')
    list_per_page = 50


class StockCorrectionChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'stock_sku', 'batch_id', 'stock_bin_id',
                    'correction_type', 'quantity', 'created_at', 'modified_at', 'inventory_csv')
    readonly_fields = ('warehouse', 'stock_sku', 'batch_id', 'stock_bin_id', 'correction_type', 'quantity',
                       'created_at', 'modified_at', 'inventory_csv')
    list_per_page = 50


class OrderReleaseAdmin(admin.ModelAdmin):
    list_display = (
        'warehouse', 'sku', 'transaction_id', 'order_number', 'warehouse_internal_inventory_reserve',
        'warehouse_internal_inventory_release',
        'reserved_time', 'release_time', 'created_at')
    readonly_fields = (
        'warehouse', 'sku', 'transaction_id', 'warehouse_internal_inventory_reserve', 'warehouse_internal_inventory_release',
        'reserved_time',
        'release_time', 'created_at')

    search_fields = ('sku__product_sku',)
    list_filter = [Warehouse, SKUFilter]
    list_per_page = 50

    def order_number(self, obj):
        try:
            if obj is None:
                pass
            return obj.warehouse_internal_inventory_release.transaction_id
        except:
            return obj.warehouse_internal_inventory_reserve.transaction_id

    order_number.short_description = 'Order Number'

    class Media:
        pass


class AuditAdmin(admin.ModelAdmin):
    """
    This class is used to view the Stock(Movement) form Admin Panel
    """

    list_display = ('id', 'uploaded_by', 'created_at', 'upload_csv')
    list_display_links = None
    list_per_page = 50
    change_list_template = 'admin/wms/audit_change_list.html'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(AuditAdmin, self).get_urls()
        urls = [
                   url(
                       r'^audit-download-csv/$',
                       self.admin_site.admin_view(audit_download),
                       name="audit-download"
                   ),
                   url(
                       r'^audit-upload-csv/$',
                       self.admin_site.admin_view(audit_upload),
                       name="audit-upload"
                   )
               ] + urls
        return urls

    def get_queryset(self, request):
        """

        :param request: get request
        :return: queryset
        """
        qs = super(AuditAdmin, self).get_queryset(request)
        return qs


admin.site.register(Bin, BinAdmin)
admin.site.register(In, InAdmin)
admin.site.register(InventoryType, InventoryTypeAdmin)
admin.site.register(Putaway, PutAwayAdmin)
admin.site.register(PutawayBinInventory, PutawayBinInventoryAdmin)
admin.site.register(BinInventory, BinInventoryAdmin)
admin.site.register(Out, OutAdmin)
admin.site.register(Pickup, PickupAdmin)
admin.site.register(PickupBinInventory, PickupBinInventoryAdmin)
admin.site.register(StockMovementCSVUpload, StockMovementCSVUploadAdmin)
admin.site.register(WarehouseInventory, WarehouseInventoryAdmin)
admin.site.register(InventoryState, InventoryStateAdmin)
admin.site.register(WarehouseInternalInventoryChange, WarehouseInternalInventoryChangeAdmin)
admin.site.register(BinInternalInventoryChange, BinInternalInventoryChangeAdmin)
admin.site.register(StockCorrectionChange, StockCorrectionChangeAdmin)
admin.site.register(OrderReserveRelease, OrderReleaseAdmin)
admin.site.register(Audit, AuditAdmin)
