# python imports
import logging
import csv

# django imports
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse

# app imports
from .views import bins_upload, put_away, CreatePickList
from import_export import resources
from .models import (Bin, InventoryType, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup, PickupBinInventory,
                     WarehouseInventory, InventoryState, WarehouseInternalInventoryChange, StockMovementCSVUpload,
                     BinInternalInventoryChange, StockCorrectionChange, OrderReserveRelease)
from .forms import (BinForm, InForm, PutAwayForm, PutAwayBinInventoryForm, BinInventoryForm, OutForm, PickupForm,
                    StockMovementCSVUploadAdminForm)
from barCodeGenerator import barcodeGen


# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BinResource(resources.ModelResource):
    info_logger.info("Bin Resource Admin has been called.")
    class Meta:
        model = Bin
        exclude = ('created_at', 'modified_at')


class BinAdmin(admin.ModelAdmin):
    info_logger.info("Bin Admin has been called.")
    form = BinForm
    resource_class = BinResource
    actions = ['download_csv_for_bins',]
    list_display = ('warehouse', 'bin_id', 'bin_type', 'created_at', 'modified_at', 'is_active', 'download_bin_id_barcode')
    readonly_fields = ['bin_barcode','barcode_image','download_bin_id_barcode']

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
        info_logger.info("download bin barcode method has been called.")
        if not obj.bin_barcode:
            return format_html("-")
        return format_html(
            "<a href='data:image/png;base64,{}' download='{}'>{}</a>".format(barcodeGen(obj.bin_id), obj.bin_id, obj.
                                                                             bin_id)
        )
    download_bin_id_barcode.short_description = 'Download Batch ID Barcode'

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

    download_csv_for_bins.short_description = "Download CSV of selected bins"


class InAdmin(admin.ModelAdmin):
    info_logger.info("In Admin has been called.")
    form = InForm
    list_display = ('warehouse', 'sku', 'quantity')


class PutAwayAdmin(admin.ModelAdmin):
    info_logger.info("Put Away Admin has been called.")
    form = PutAwayForm
    list_display = ('warehouse','putaway_type', 'putaway_type_id', 'sku', 'batch_id','quantity','putaway_quantity')


class PutawayBinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Put Away Bin Inventory Admin has been called.")
    form = PutAwayBinInventoryForm
    list_display = ('warehouse', 'putaway', 'bin', 'putaway_quantity', 'created_at')


class InventoryTypeAdmin(admin.ModelAdmin):
    info_logger.info("Inventory Type Admin has been called.")
    list_display = ('inventory_type',)


class BinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Bin Inventory Admin has been called.")
    form = BinInventoryForm
    list_select_related = ('warehouse', 'sku', 'bin', 'inventory_type')
    list_display = ('batch_id','warehouse', 'sku', 'bin','inventory_type', 'quantity', 'in_stock')
    readonly_fields = ('batch_id','warehouse', 'sku', 'bin','inventory_type', 'in_stock')
    list_filter = ('warehouse', 'sku', 'batch_id')
    list_per_page = 50


class OutAdmin(admin.ModelAdmin):
    info_logger.info("Out Admin has been called.")
    form = OutForm
    list_display = ('warehouse', 'out_type', 'out_type_id', 'sku', 'quantity')
    readonly_fields = ('warehouse', 'out_type', 'out_type_id', 'sku', 'quantity')

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
    list_display = ('warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'quantity','pickup_quantity','status')
    # readonly_fields = ('quantity','pickup_quantity',)


class PickupBinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Pick up Bin Inventory Admin has been called.")

    list_display = ('warehouse', 'pickup', 'batch_id', 'bin','quantity', 'pickup_quantity','created_at')
    list_select_related = ('warehouse', 'pickup', 'bin')
    readonly_fields = ('warehouse', 'pickup', 'batch_id', 'bin','created_at')


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
    list_display = ('warehouse', 'sku', 'inventory_type', 'inventory_state', 'quantity', 'in_stock', 'created_at', 'modified_at')
    list_select_related = ('warehouse', 'inventory_type', 'inventory_state', 'sku')
    readonly_fields = ('warehouse', 'sku', 'inventory_type', 'inventory_state', 'quantity', 'in_stock', 'created_at', 'modified_at')


class InventoryStateAdmin(admin.ModelAdmin):
    list_display = ('inventory_state',)
    readonly_fields = ('inventory_state',)


class WarehouseInternalInventoryChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'transaction_type', 'transaction_id', 'initial_stage', 'final_stage', 'quantity', 'created_at', 'modified_at', 'inventory_csv')
    list_select_related = ('warehouse', 'sku')
    readonly_fields = ('warehouse', 'sku', 'transaction_type', 'transaction_id', 'initial_stage', 'final_stage', 'quantity', 'created_at', 'modified_at')


class BinInternalInventoryChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'batch_id', 'initial_inventory_type', 'final_inventory_type', 'initial_bin',
                    'final_bin', 'quantity','created_at', 'modified_at', 'inventory_csv')


class StockCorrectionChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'stock_sku', 'batch_id', 'stock_bin_id',
                    'correction_type', 'quantity', 'created_at', 'modified_at', 'inventory_csv')

class OrderReleaseAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'warehouse_internal_inventory_reserve', 'warehouse_internal_inventory_release', 'reserved_time', 'release_time', 'created_at')
    readonly_fields = ('warehouse', 'sku', 'warehouse_internal_inventory_reserve', 'warehouse_internal_inventory_release', 'reserved_time', 'release_time', 'created_at')

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
