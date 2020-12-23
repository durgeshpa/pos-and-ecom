# python imports
import logging
import csv
from io import StringIO
from datetime import datetime

from dal_admin_filters import AutocompleteFilter
# django imports
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django_admin_listfilter_dropdown.filters import ChoiceDropdownFilter, DropdownFilter
from rangefilter.filter import DateTimeRangeFilter, DateRangeFilter

from retailer_to_sp.models import Invoice, Trip
from gram_to_brand.models import GRNOrder
from products.models import ProductVendorMapping
from products.models import ProductVendorMapping, ProductPrice
from retailer_backend.admin import InputFilter
# app imports
from .common_functions import get_expiry_date
from .filters import ExpiryDateFilter
from .views import bins_upload, put_away, CreatePickList, audit_download, audit_upload, bulk_putaway
from import_export import resources
from .models import (Bin, InventoryType, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup,
                     PickupBinInventory,
                     WarehouseInventory, InventoryState, WarehouseInternalInventoryChange, StockMovementCSVUpload,
                     BinInternalInventoryChange, StockCorrectionChange, OrderReserveRelease, Audit,
                     ExpiredInventoryMovement)
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


class InitialBinIDFilter(InputFilter):
    title = 'Initial Bin ID'
    parameter_name = 'initial_bin'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(initial_bin__bin_id=value)
        return queryset


class FinalBinIDFilter(InputFilter):
    title = 'Final Bin ID'
    parameter_name = 'final_bin'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(final_bin__bin_id=value)
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


class InitialInventoryTypeFilter(AutocompleteFilter):
    title = 'Initial Inventory Type'
    field_name = 'initial_inventory_type'
    autocomplete_url = 'inventory-type-autocomplete'


class FinalInventoryTypeFilter(AutocompleteFilter):
    title = 'Final Inventory Type'
    field_name = 'final_inventory_type'
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


class OrderNumberFilterForOrderRelease(InputFilter):
    title = 'Order Number'
    parameter_name = 'warehouse_internal_inventory_release'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(warehouse_internal_inventory_release__transaction_id=value)
        return queryset


class OrderNumberFilterForPickupBinInventory(InputFilter):
    title = 'Order / Repackaging Number'
    parameter_name = 'pickup'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(pickup__pickup_type_id=value)
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
    list_display = ('id', 'warehouse', 'sku', 'batch_id', 'in_type', 'in_type_id', 'inventory_type',
                    'quantity', 'expiry_date')
    readonly_fields = ('warehouse', 'in_type', 'in_type_id', 'sku', 'batch_id', 'inventory_type',
                       'quantity', 'expiry_date')
    search_fields = ('batch_id', 'in_type_id', 'sku__product_sku',)
    list_filter = [Warehouse, BatchIdFilter, SKUFilter, InTypeIDFilter, 'in_type',
                   ('expiry_date', DateRangeFilter)]
    list_per_page = 50

    class Media:
        pass


class PutAwayAdmin(admin.ModelAdmin):
    info_logger.info("Put Away Admin has been called.")
    form = PutAwayForm
    list_display = (
        'putaway_user', 'warehouse', 'sku', 'batch_id', 'putaway_type', 'putaway_type_id', 'grn_id', 'trip_id',
        'inventory_type', 'quantity',
        'putaway_quantity', 'created_at', 'modified_at')
    actions = ['download_bulk_put_away_csv']
    readonly_fields = ('warehouse', 'putaway_type', 'putaway_type_id', 'sku', 'batch_id', 'inventory_type',
                       'quantity', 'putaway_quantity',)
    search_fields = ('putaway_user__phone_number', 'batch_id', 'sku__product_sku',)
    list_filter = [Warehouse, BatchIdFilter, SKUFilter, ('putaway_type', DropdownFilter), PutawayuserFilter,
                   ('created_at', DateTimeRangeFilter), ('modified_at', DateTimeRangeFilter)]
    list_per_page = 50

    def grn_id(self, obj):
        try:
            if obj.putaway_type == 'GRN':
                in_type_id = In.objects.filter(id=obj.putaway_type_id).last().in_type_id
                grn_id = GRNOrder.objects.filter(grn_id=in_type_id).last().id
                return format_html("<a href='/admin/gram_to_brand/grnorder/%s/change/'> %s </a>" % (str(grn_id), str(in_type_id)))
            else:
                return '-'
        except:
            return '-'

    def trip_id(self, obj):
        try:
            if obj.putaway_type == 'RETURNED':
                invoice_number = Invoice.objects.filter(invoice_no=obj.putaway_type_id).last().shipment.trip.dispatch_no
                trip_id = Trip.objects.filter(dispatch_no=invoice_number).last().id
                return format_html(
                    "<a href='/admin/retailer_to_sp/cart/trip-planning/%s/change/'> %s </a>" % (str(trip_id), str(invoice_number)))
            else:
                return '-'
        except:
            return '-'

    def download_bulk_put_away_csv(self, request, queryset):
        """
        :param request: get request
        :param queryset: Put Away queryset
        :return: csv file
        """
        f = StringIO()
        writer = csv.writer(f)
        # set the header name
        writer.writerow(["Put Away User", "Warehouse", "Put Away Type", "Put Away Type ID", "SKU", "Batch ID",
                         "Quantity", "Put Away Quantity", "Created At", "Modified At"])

        for query in queryset:
            # iteration for selected id from Admin Dashboard and get the instance
            putaway = Putaway.objects.get(id=query.id)
            # get object from queryset
            writer.writerow([putaway.putaway_user, putaway.warehouse_id,
                             putaway.putaway_type, putaway.putaway_type_id,
                             putaway.sku.product_name + '-' + putaway.sku.product_sku,
                             putaway.batch_id, putaway.quantity, putaway.putaway_quantity,
                             putaway.created_at, putaway.modified_at])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=putaway_download.csv'
        return response

    download_bulk_put_away_csv.short_description = "Download Bulk Put Away Data in CSV"

    class Media:
        pass


class PutawayBinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Put Away Bin Inventory Admin has been called.")
    form = PutAwayBinInventoryForm
    list_display = ('warehouse', 'sku', 'batch_id', 'putaway_type', 'putaway_id', 'bin_id', 'inventory_type',
                    'putaway_quantity', 'putaway_status', 'created_at', 'modified_at')
    actions = ['download_bulk_put_away_bin_inventory_csv', 'bulk_approval_for_putaway']
    readonly_fields = ['warehouse', 'sku', 'batch_id', 'putaway_type', 'putaway', 'inventory_type', 'putaway_quantity']
    search_fields = ('batch_id', 'sku__product_sku', 'bin__bin__bin_id')
    list_filter = [
        Warehouse, BatchIdFilter, SKUFilter, BinIdFilter, ('putaway_type', DropdownFilter), 'putaway_status',
        ('created_at', DateTimeRangeFilter), ('modified_at', DateTimeRangeFilter)]
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
        writer.writerow(["Warehouse", "SKU", "Batch ID ", "Put Away Type",
                         "Put Away ID", "Bin ID", "Put Away Quantity", "Put Away Status",
                         "Created At", "Modified At"])

        for query in queryset:
            # iteration for selected id from Admin Dashboard and get the instance
            putaway_bin_inventory = PutawayBinInventory.objects.get(id=query.id)
            # get object from queryset
            writer.writerow([putaway_bin_inventory.warehouse_id,
                             putaway_bin_inventory.sku.product_name + '-' + putaway_bin_inventory.sku.product_sku,
                             putaway_bin_inventory.batch_id, putaway_bin_inventory.putaway_type,
                             putaway_bin_inventory.putaway_id,
                             putaway_bin_inventory.bin.bin.bin_id,
                             putaway_bin_inventory.putaway_quantity,
                             putaway_bin_inventory.putaway_status,
                             putaway_bin_inventory.created_at,
                             putaway_bin_inventory.modified_at])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=putaway_bin_inventory_download.csv'
        return response

    def bulk_approval_for_putaway(self, request, queryset):
        argument_list = []
        for query in queryset:
            if query.putaway_status is True:
                pass
            else:
                argument_list.append(query)
            if len(argument_list) == 0:
                response = messages.error(request, "Please select at least one Deactivate PutAway Bin Inventory for Bulk Approval.")
                return response
        try:
            response = bulk_putaway(self, request, argument_list)
            if response[1] is True:
                messages.success(request, response[0])
                return response
            else:
                messages.error(request, response[0])
                return response
        except Exception as e:
            error_logger.error(e)
            messages.error(request, "Something went wrong, Please try again!!")
            return response

    def putaway_id(self, obj):
        return obj.putaway_id

    def inventory_type(self, obj):
        return obj.putaway.inventory_type

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
    bulk_approval_for_putaway.short_description = "Bulk Approval for Put Away"

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
    list_display = ('batch_id', 'warehouse', 'sku', 'bin', 'inventory_type', 'quantity', 'in_stock', 'created_at',
                    'modified_at', 'expiry_date')
    readonly_fields = ['warehouse', 'bin', 'sku', 'batch_id', 'inventory_type', 'quantity', 'in_stock']
    search_fields = ('batch_id', 'sku__product_sku', 'bin__bin_id', 'created_at', 'modified_at',)
    list_filter = [BinIDFilterForBinInventory, Warehouse, BatchIdFilter, SKUFilter, InventoryTypeFilter,
                   ExpiryDateFilter]
    list_per_page = 50

    class Media:
        js = ('admin/js/picker.js',)

    def expiry_date(self, obj):
        return get_expiry_date(obj.batch_id)

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
            #product_mrp = ProductVendorMapping.objects.filter(product=obj.sku).last()

            temp_data = {"qty": 1, "data": {"SKU": obj.sku.product_name,
                                            "Batch":obj.batch_id,
                                            "MRP": obj.sku.product_mrp if obj.sku.product_mrp else ''}}
            product_id = str(obj.sku.id).zfill(5)
            barcode_id = str("2" + product_id + str(obj.batch_id[-6:]))
            bin_id_list[barcode_id] = temp_data
        return merged_barcode_gen(bin_id_list)

    download_barcode.short_description = "Download Barcode List"


class OutAdmin(admin.ModelAdmin):
    info_logger.info("Out Admin has been called.")
    form = OutForm
    list_display = ('warehouse', 'out_type', 'out_type_id', 'sku', 'batch_id', 'inventory_type',
                    'quantity', 'created_at', 'modified_at')
    readonly_fields = ('warehouse', 'out_type', 'out_type_id', 'sku', 'batch_id', 'inventory_type',
                       'quantity', 'created_at', 'modified_at')
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
    list_display = ('warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'inventory_type', 'quantity',
                    'pickup_quantity', 'status', 'completed_at')
    readonly_fields = (
    'warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'inventory_type', 'quantity', 'pickup_quantity', 'status', 'out',)
    search_fields = ('pickup_type_id', 'sku__product_sku',)
    list_filter = [Warehouse, PicktypeIDFilter, SKUFilter, ('status', DropdownFilter), 'pickup_type']
    list_per_page = 50

    class Media:
        pass


class PickupBinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Pick up Bin Inventory Admin has been called.")

    list_display = ('warehouse', 'batch_id', 'order_number', 'pickup_type', 'bin_id', 'inventory_type',
                    'bin_quantity', 'quantity', 'pickup_quantity', 'created_at', 'last_picked_at', 'pickup_remarks')
    list_select_related = ('warehouse', 'pickup', 'bin')
    readonly_fields = ('bin_quantity', 'quantity', 'pickup_quantity', 'warehouse', 'pickup', 'batch_id', 'bin',
                       'created_at', 'last_picked_at', 'pickup_remarks')
    search_fields = ('batch_id', 'bin__bin__bin_id')
    list_filter = [Warehouse, BatchIdFilter, BinIDFilterForPickupBinInventory, OrderNumberFilterForPickupBinInventory, ('created_at', DateTimeRangeFilter)]
    list_per_page = 50

    def order_number(self, obj):
        return obj.pickup.pickup_type_id

    def pickup_type(self, obj):
        return obj.pickup.pickup_type

    def bin_id(self, obj):
        return obj.bin.bin.bin_id

    def pickup_remarks(self,obj):
        return obj.remarks;

    def inventory_type(self, obj):
        return obj.pickup.inventory_type

    class Media:
        pass

    order_number.short_description = 'Order / Repackaging Number'
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
    list_filter = [Warehouse, SKUFilter, BatchIdFilter, InitialInventoryTypeFilter, FinalInventoryTypeFilter,
                   InitialBinIDFilter, FinalBinIDFilter, ('transaction_type', DropdownFilter),
                   TransactionIDFilter]

    list_per_page = 50

    class Media:
        pass


class StockCorrectionChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'stock_sku', 'batch_id', 'stock_bin_id',
                    'correction_type', 'inventory_type', 'quantity', 'created_at', 'modified_at', 'inventory_csv')
    readonly_fields = ('warehouse', 'stock_sku', 'batch_id', 'stock_bin_id', 'correction_type', 'inventory_type', 'quantity',
                       'created_at', 'modified_at', 'inventory_csv')
    list_per_page = 50


class OrderReleaseAdmin(admin.ModelAdmin):
    list_display = (
        'warehouse', 'sku', 'release_type', 'ordered_quantity', 'transaction_id', 'order_number', 'warehouse_internal_inventory_reserve',
        'warehouse_internal_inventory_release',
        'reserved_time', 'release_time', 'created_at')
    readonly_fields = (
        'warehouse', 'sku','release_type', 'ordered_quantity', 'transaction_id', 'warehouse_internal_inventory_reserve', 'warehouse_internal_inventory_release',
        'reserved_time',
        'release_time', 'created_at')

    search_fields = ('sku__product_sku',)
    list_filter = [Warehouse, SKUFilter, TransactionIDFilter, OrderNumberFilterForOrderRelease, 'release_type']
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


class ExpiredInventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'batch_id', 'bin', 'mrp', 'quantity', 'expiry_date',
                    'status', 'created_at',)
    readonly_fields = ('warehouse', 'sku', 'batch_id', 'bin', 'mrp', 'inventory_type', 'quantity', 'expiry_date',
                       'created_at')
    list_filter = [SKUFilter, BatchIdFilter, BinIDFilterForBinInventory, ('created_at', DateRangeFilter)]
    list_per_page = 50
    actions = ['download_tickets', 'close_tickets']
    date_hierarchy = 'created_at'

    def download_tickets(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        # set the header name
        writer.writerow(["warehouse", "sku", "batch_id", "bin", "quantity", "expiry_date",
                         "status", "created_at",])

        for query in queryset:
            ticket = ExpiredInventoryMovement.objects.get(id=query.id)
            writer.writerow([ticket.warehouse, ticket.sku, ticket.batch_id, ticket.bin, ticket.quantity,
                             ticket.expiry_date, ticket.status, ticket.created_at])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=expired-inventory-movement.csv'
        return response

    def close_tickets(self, request, queryset):

        for query in queryset:
            ticket = ExpiredInventoryMovement.objects.get(id=query.id,
                                                          status=ExpiredInventoryMovement.STATUS_CHOICE.OPEN)
            if ticket:
                ticket.status = ExpiredInventoryMovement.STATUS_CHOICE.CLOSED
                ticket.save()

    close_tickets.short_description = "Close selected tickets"
    download_tickets.short_description = "Download selected items as CSV"


admin.site.register(Bin, BinAdmin)
admin.site.register(In, InAdmin)
# admin.site.register(InventoryType, InventoryTypeAdmin)
admin.site.register(Putaway, PutAwayAdmin)
admin.site.register(PutawayBinInventory, PutawayBinInventoryAdmin)
admin.site.register(BinInventory, BinInventoryAdmin)
admin.site.register(Out, OutAdmin)
admin.site.register(Pickup, PickupAdmin)
admin.site.register(PickupBinInventory, PickupBinInventoryAdmin)
admin.site.register(StockMovementCSVUpload, StockMovementCSVUploadAdmin)
admin.site.register(WarehouseInventory, WarehouseInventoryAdmin)
# admin.site.register(InventoryState, InventoryStateAdmin)
admin.site.register(WarehouseInternalInventoryChange, WarehouseInternalInventoryChangeAdmin)
admin.site.register(BinInternalInventoryChange, BinInternalInventoryChangeAdmin)
admin.site.register(StockCorrectionChange, StockCorrectionChangeAdmin)
admin.site.register(OrderReserveRelease, OrderReleaseAdmin)
admin.site.register(Audit, AuditAdmin)
admin.site.register(ExpiredInventoryMovement, ExpiredInventoryMovementAdmin)
