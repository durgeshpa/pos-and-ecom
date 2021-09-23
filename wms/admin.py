# python imports
import csv
import logging
from io import StringIO

from dal_admin_filters import AutocompleteFilter
# django imports
from django.contrib import admin, messages
from django.contrib.admin import AllValuesFieldListFilter
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django_admin_listfilter_dropdown.filters import DropdownFilter
from import_export import resources
from rangefilter.filter import DateTimeRangeFilter, DateRangeFilter

from audit.models import AUDIT_LEVEL_CHOICES
from barCodeGenerator import merged_barcode_gen
from gram_to_brand.models import GRNOrder
from retailer_backend.admin import InputFilter
from retailer_to_sp.models import Invoice, Trip
# app imports
from services.views import InOutLedgerFormView, InOutLedgerReport
from .common_functions import get_expiry_date
from .filters import ExpiryDateFilter, PickupStatusFilter
from .forms import (BinForm, InForm, PutAwayForm, PutAwayBinInventoryForm, BinInventoryForm, OutForm, PickupForm,
                    StockMovementCSVUploadAdminForm, ZoneForm, WarehouseAssortmentForm, QCAreaForm)
from .models import (Bin, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup,
                     PickupBinInventory,
                     WarehouseInventory, WarehouseInternalInventoryChange, StockMovementCSVUpload,
                     BinInternalInventoryChange, StockCorrectionChange, OrderReserveRelease, Audit,
                     ExpiredInventoryMovement, Zone, WarehouseAssortment, QCArea, ZonePickerUserAssignmentMapping,
                     ZonePutawayUserAssignmentMapping)
from .views import bins_upload, put_away, CreatePickList, audit_download, audit_upload, bulk_putaway, \
    WarehouseAssortmentDownloadSampleCSV, WarehouseAssortmentUploadCsvView

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
    autocomplete_url = 'warehouses-autocomplete'


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


class CartNumberFilterForOrderRelease(InputFilter):
    title = 'Cart Number'
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


class SupervisorFilter(AutocompleteFilter):
    title = 'Supervisor'
    field_name = 'supervisor'
    autocomplete_url = 'supervisor-autocomplete'


class CoordinatorFilter(AutocompleteFilter):
    title = 'Coordinator'
    field_name = 'coordinator'
    autocomplete_url = 'coordinator-autocomplete'


class ZoneFilter(AutocompleteFilter):
    title = 'Zone'
    field_name = 'zone'
    autocomplete_url = 'zone-autocomplete'


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    autocomplete_url = 'users-autocomplete'


class PutawayUserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    autocomplete_url = 'all-putaway-users-autocomplete'


class PickerUserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    autocomplete_url = 'all-picker-users-autocomplete'


class ParentProductFilter(AutocompleteFilter):
    title = 'Product'
    field_name = 'product'
    autocomplete_url = 'parent-product-autocomplete'


class BinAdmin(admin.ModelAdmin):
    info_logger.info("Bin Admin has been called.")
    form = BinForm
    resource_class = BinResource
    actions = ['download_csv_for_bins', 'download_barcode']
    list_display = ('warehouse', 'bin_id', 'bin_type', 'created_at', 'modified_at', 'is_active','bin_barcode_txt',
                    'zone', 'download_bin_id_barcode')
    # readonly_fields = ['warehouse', 'bin_id', 'bin_type', 'bin_barcode', 'barcode_image',
    #                    'download_bin_id_barcode', 'download_barcode_image']
    search_fields = ('bin_id',)
    list_filter = [BinIdFilter, ZoneFilter,
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

    """
        Default single virtual bin is created for Franchise shops. Cannot be added, changed or deleted.
    """
    def has_change_permission(self, request, obj=None):
        if obj and obj.warehouse and obj.warehouse.shop_type.shop_type == 'f':
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.warehouse and obj.warehouse.shop_type.shop_type == 'f':
            return False
        return True


class InAdmin(admin.ModelAdmin):
    info_logger.info("In Admin has been called.")
    form = InForm
    list_display = ('id', 'warehouse', 'sku', 'batch_id', 'in_type', 'in_type_id', 'inventory_type',
                    'quantity_display', 'weight_in_kg', 'manufacturing_date', 'expiry_date')
    readonly_fields = ('warehouse', 'in_type', 'in_type_id', 'sku', 'batch_id', 'inventory_type',
                       'quantity', 'manufacturing_date', 'expiry_date')
    search_fields = ('batch_id', 'in_type_id', 'sku__product_sku',)
    list_filter = [Warehouse, BatchIdFilter, SKUFilter, InTypeIDFilter, 'in_type',
                   ('expiry_date', DateRangeFilter)]
    list_per_page = 50

    def quantity_display(self, obj):
        return obj.quantity

    quantity_display.short_description = "Quantity"

    def weight_in_kg(self, obj):
        return (obj.weight / 1000) if obj.sku.repackaging_type == 'packing_material' else '-'

    class Media:
        pass


    def get_urls(self):
        from django.conf.urls import url
        urls = super(InAdmin, self).get_urls()
        urls = [
           url(
               r'^in-out-ledger-report/$',
               self.admin_site.admin_view(InOutLedgerReport.as_view()),
               name="in-out-ledger-report"
           ),
           url(
               r'^in-out-ledger-form/$',
               self.admin_site.admin_view(InOutLedgerFormView.as_view()),
               name="in-out-ledger-form"
           )
        ] + urls
        return urls


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
                    'putaway_quantity', 'putaway_status', 'sku_bin_inventory', 'created_at', 'modified_at')
    actions = ['download_bulk_put_away_bin_inventory_csv', 'bulk_approval_for_putaway']
    readonly_fields = ['warehouse', 'sku', 'batch_id', 'putaway_type', 'putaway', 'inventory_type', 'putaway_quantity']
    search_fields = ('batch_id', 'sku__product_sku', 'bin__bin__bin_id')
    list_filter = [
        Warehouse, BatchIdFilter, SKUFilter, BinIdFilter, ('putaway_type', DropdownFilter), 'putaway_status',
        ('created_at', DateTimeRangeFilter), ('modified_at', DateTimeRangeFilter)]
    list_per_page = 50

    @staticmethod
    def sku_bin_inventory(obj):
        ret_url = '/admin/wms/bininventory/?warehouse__id__exact=%s&sku=%s' % (obj.warehouse.id, obj.sku.product_sku)
        onclick = 'window.open("%s", "_blank", "toolbar=yes,scrollbars=yes,resizable=yes,top=100,left=300,width=800,' \
                  'height=500");' % ret_url
        return format_html("<a href='#' onclick='%s'>View Sku Bin Inventory</a>" % onclick)

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
    list_display = ('batch_id', 'warehouse', 'sku', 'bin', 'inventory_type', 'quantity_display', 'weight_in_kg', 'to_be_picked_qty',
                    'in_stock', 'created_at', 'modified_at', 'expiry_date')
    readonly_fields = ['warehouse', 'bin', 'sku', 'batch_id', 'inventory_type', 'quantity', 'in_stock']
    search_fields = ('batch_id', 'sku__product_sku', 'bin__bin_id', 'created_at', 'modified_at',)
    list_filter = [BinIDFilterForBinInventory, Warehouse, BatchIdFilter, SKUFilter, InventoryTypeFilter,
                   ExpiryDateFilter]
    list_per_page = 50

    class Media:
        js = ('admin/js/picker.js',)

    def quantity_display(self, obj):
        return obj.quantity if obj.sku.repackaging_type != 'packing_material' else '-'

    quantity_display.short_description = "Quantity"

    def weight_in_kg(self, obj):
        return (obj.weight / 1000) if obj.sku.repackaging_type == 'packing_material' else '-'

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
                    'quantity_display', 'weight_in_kg', 'created_at', 'modified_at')
    readonly_fields = ('warehouse', 'out_type', 'out_type_id', 'sku', 'batch_id', 'inventory_type',
                       'quantity', 'created_at', 'modified_at')
    list_filter = [Warehouse, ('out_type', DropdownFilter), SKUFilter, BatchIdFilter, OutTypeIDFilter]
    list_per_page = 50

    class Media:
        pass

    def quantity_display(self, obj):
        return obj.quantity

    quantity_display.short_description = "Quantity"

    def weight_in_kg(self, obj):
        return (obj.weight / 1000) if obj.sku.repackaging_type == 'packing_material' else '-'

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
    list_display = ('warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'zone', 'inventory_type', 'quantity',
                    'pickup_quantity', 'status', 'completed_at')
    readonly_fields = (
    'warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'inventory_type', 'quantity', 'pickup_quantity', 'status', 'out',)
    search_fields = ('pickup_type_id', 'sku__product_sku',)
    list_filter = [Warehouse, PicktypeIDFilter, SKUFilter, ZoneFilter, ('status', DropdownFilter), 'pickup_type']
    list_per_page = 50

    class Media:
        pass


class PickupBinInventoryAdmin(admin.ModelAdmin):
    info_logger.info("Pick up Bin Inventory Admin has been called.")

    list_display = ('warehouse', 'batch_id', 'order_number', 'pickup_type', 'bin_id', 'inventory_type',
                    'bin_quantity', 'quantity', 'pickup_quantity', 'created_at', 'last_picked_at', 'pickup_status',
                    'pickup_remarks', 'add_audit_link')
    list_select_related = ('warehouse', 'pickup', 'bin')
    readonly_fields = ('bin_quantity', 'quantity', 'pickup_quantity', 'warehouse', 'pickup', 'batch_id', 'bin',
                       'created_at', 'last_picked_at', 'pickup_remarks')
    search_fields = ('batch_id', 'bin__bin__bin_id')
    list_filter = [Warehouse, BatchIdFilter, BinIDFilterForPickupBinInventory, OrderNumberFilterForPickupBinInventory,
                   PickupStatusFilter, ('remarks', AllValuesFieldListFilter), ('created_at', DateTimeRangeFilter)]
    list_per_page = 50
    actions = ['download_csv']

    def order_number(self, obj):
        return obj.pickup.pickup_type_id

    def pickup_type(self, obj):
        return obj.pickup.pickup_type

    def bin_id(self, obj):
        return obj.bin.bin.bin_id

    def pickup_remarks(self, obj):
        return obj.remarks

    def inventory_type(self, obj):
        return obj.pickup.inventory_type

    def pickup_status(self, obj):
        if obj.pickup.status == Pickup.pickup_status_choices.picking_complete:
            if obj.quantity != obj.pickup_quantity:
                return PickupBinInventory.PICKUP_STATUS_CHOICES[PickupBinInventory.PICKUP_STATUS_CHOICES.PARTIAL]
            return PickupBinInventory.PICKUP_STATUS_CHOICES[PickupBinInventory.PICKUP_STATUS_CHOICES.FULL]
        elif obj.pickup.status == Pickup.pickup_status_choices.picking_cancelled:
            return PickupBinInventory.PICKUP_STATUS_CHOICES[PickupBinInventory.PICKUP_STATUS_CHOICES.CANCELLED]
        return PickupBinInventory.PICKUP_STATUS_CHOICES[PickupBinInventory.PICKUP_STATUS_CHOICES.PENDING]

    def add_audit_link(self, obj):
        if obj.pickup.status == 'picking_complete':
            if obj.quantity != obj.pickup_quantity:
                if obj.audit_no:
                    return obj.audit_no
                return format_html(
                    "<a href = '/admin/audit/auditdetail/add/?warehouse=%s&audit_level=%s&sku=%s&pbi=%s' class ='addlink' > Audit</a>" % (
                    obj.warehouse_id, AUDIT_LEVEL_CHOICES.PRODUCT, obj.pickup.sku.id, obj.id))

    def download_csv(self, request, queryset):
        f = StringIO()
        writer = csv.writer(f)
        # set the header name
        writer.writerow(['warehouse', 'batch_id', 'order_number', 'pickup_type', 'bin_id', 'inventory_type',
                         'bin_quantity', 'quantity', 'pickup_quantity', 'pickup_status',
                         'pickup_remarks', 'created_at', 'last_picked_at' ])

        for item in queryset:
            writer.writerow([item.warehouse, item.batch_id, self.order_number(item), self.pickup_type(item),
                             self.bin_id(item), self.inventory_type(item), item.bin_quantity, item.quantity,
                             item.pickup_quantity, self.pickup_status(item), self.pickup_remarks(item),
                             item.created_at, item.last_picked_at])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=pickup_bin_inventory.csv'
        return response
    add_audit_link.short_description = 'Add Audit'
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
        'warehouse', 'sku', 'inventory_type', 'inventory_state', 'quantity_display', 'weight_in_kg', 'in_stock', 'created_at',
        'modified_at')
    list_select_related = ('warehouse', 'inventory_type', 'inventory_state', 'sku')

    readonly_fields = (
    'warehouse', 'sku', 'inventory_type', 'inventory_state', 'in_stock', 'created_at', 'modified_at', 'quantity',)
    search_fields = ('sku__product_sku',)
    list_filter = [Warehouse, SKUFilter, InventoryTypeFilter, InventoryStateFilter, ('created_at', DateTimeRangeFilter),
                   ('modified_at', DateTimeRangeFilter)]
    list_per_page = 50

    def quantity_display(self, obj):
        return obj.quantity if obj.sku.repackaging_type != 'packing_material' else '-'

    quantity_display.short_description = "Quantity"

    def weight_in_kg(self, obj):
        return (obj.weight / 1000) if obj.sku.repackaging_type == 'packing_material' else '-'

    class Media:
        pass


class InventoryStateAdmin(admin.ModelAdmin):
    list_display = ('inventory_state',)
    list_per_page = 50


class WarehouseInternalInventoryChangeAdmin(admin.ModelAdmin):
    list_display = (
        'warehouse', 'sku', 'transaction_type', 'transaction_id', 'inventory_type', 'inventory_state', 'quantity_display',
        'weight_in_kg', 'created_at', 'modified_at', 'inventory_csv')
    list_select_related = ('warehouse', 'sku')
    readonly_fields = (
        'inventory_type', 'inventory_state', 'inventory_csv', 'status', 'warehouse', 'sku', 'transaction_type', 'transaction_id',
        'initial_type', 'initial_stage',
        'final_type', 'final_stage', 'quantity_display', 'created_at', 'modified_at')

    search_fields = ('sku__product_sku', 'transaction_id',)
    list_filter = [Warehouse, ProductSKUFilter, TransactionIDFilter, InventoryTypeFilter, InventoryStateFilter,
                    ('transaction_type', DropdownFilter), ('created_at', DateTimeRangeFilter),
                   ('modified_at', DateTimeRangeFilter)]
    list_per_page = 50

    def quantity_display(self, obj):
        return obj.quantity

    quantity_display.short_description = "Quantity"

    def weight_in_kg(self, obj):
        return (obj.weight / 1000) if obj.sku.repackaging_type == 'packing_material' else '-'

    class Media:
        pass


class BinInternalInventoryChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'batch_id', 'initial_inventory_type', 'final_inventory_type', 'initial_bin',
                    'final_bin', 'transaction_type', 'transaction_id',
                    'quantity_display', 'weight_in_kg', 'created_at', 'modified_at', 'inventory_csv')
    list_filter = [Warehouse, SKUFilter, BatchIdFilter, InitialInventoryTypeFilter, FinalInventoryTypeFilter,
                   InitialBinIDFilter, FinalBinIDFilter, ('transaction_type', DropdownFilter),
                   TransactionIDFilter]

    list_per_page = 50

    def quantity_display(self, obj):
        return obj.quantity

    quantity_display.short_description = "Quantity"

    def weight_in_kg(self, obj):
        return (obj.weight / 1000) if obj.sku.repackaging_type == 'packing_material' else '-'

    class Media:
        pass


class StockCorrectionChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'stock_sku', 'batch_id', 'stock_bin_id',
                    'correction_type', 'inventory_type', 'quantity_display', 'weight_in_kg', 'created_at', 'modified_at', 'inventory_csv')
    readonly_fields = ('warehouse', 'stock_sku', 'batch_id', 'stock_bin_id', 'correction_type', 'inventory_type', 'quantity',
                       'created_at', 'modified_at', 'inventory_csv')
    list_per_page = 50

    def quantity_display(self, obj):
        return obj.quantity

    quantity_display.short_description = "Quantity"

    def weight_in_kg(self, obj):
        return (obj.weight / 1000) if obj.stock_sku.repackaging_type == 'packing_material' else '-'


class OrderReleaseAdmin(admin.ModelAdmin):
    list_display = (
        'warehouse', 'sku', 'release_type', 'ordered_quantity', 'transaction_id', 'cart_number', 'warehouse_internal_inventory_reserve',
        'warehouse_internal_inventory_release',
        'reserved_time', 'release_time', 'created_at')
    readonly_fields = (
        'warehouse', 'sku','release_type', 'ordered_quantity', 'transaction_id', 'warehouse_internal_inventory_reserve', 'warehouse_internal_inventory_release',
        'reserved_time',
        'release_time', 'created_at')

    search_fields = ('sku__product_sku',)
    list_filter = [Warehouse, SKUFilter, TransactionIDFilter, CartNumberFilterForOrderRelease, 'release_type']
    list_per_page = 50

    def cart_number(self, obj):
        try:
            if obj is None:
                pass
            return obj.warehouse_internal_inventory_release.transaction_id
        except:
            return obj.warehouse_internal_inventory_reserve.transaction_id

    cart_number.short_description = 'Cart Number'

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


class ZoneAdmin(admin.ModelAdmin):
    form = ZoneForm
    list_display = ('zone_number', 'name', 'warehouse', 'supervisor', 'coordinator', 'created_at', 'updated_at',
                    'created_by', 'updated_by',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    list_filter = [Warehouse, SupervisorFilter, CoordinatorFilter,
                   ('created_at', DateRangeFilter), ('updated_at', DateRangeFilter)]
    search_fields = ('zone_number', 'name')
    list_per_page = 50

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super(ZoneAdmin, self).save_model(request, obj, form, change)

    class Media:
        pass


class WarehouseAssortmentAdmin(admin.ModelAdmin):
    form = WarehouseAssortmentForm
    list_display = ('warehouse', 'product', 'zone', 'created_at', 'updated_at', 'created_by',
                    'updated_by',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    list_filter = [Warehouse, ParentProductFilter, ZoneFilter,
                   ('created_at', DateRangeFilter), ('updated_at', DateRangeFilter)]
    list_per_page = 50

    change_list_template = 'admin/wms/warehouse_assortment_change_list.html'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(WarehouseAssortmentAdmin, self).get_urls()
        urls = [
            url(
                r'^warehouse-assortment-download-sample-csv/$',
                self.admin_site.admin_view(WarehouseAssortmentDownloadSampleCSV),
                name="warehouse-assortment-download-sample-csv"
            ),
            url(
                r'^warehouse-assortment-upload-csv/$',
                self.admin_site.admin_view(WarehouseAssortmentUploadCsvView),
                name="warehouse-assortment-upload"
            ),
        ] + urls
        return urls

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super(WarehouseAssortmentAdmin, self).save_model(request, obj, form, change)

    class Media:
        pass


class QCAreaAdmin(admin.ModelAdmin):
    form = QCAreaForm
    list_display = ('area_id', 'warehouse', 'area_type', 'is_active','area_barcode_txt', 'download_area_barcode')
    search_fields = ('area_id', 'area_barcode_txt')
    list_filter = [Warehouse, ('area_type', DropdownFilter),]
    list_per_page = 50
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super(QCAreaAdmin, self).save_model(request, obj, form, change)

    class Media:
        js = ('admin/js/picker.js',)

    def download_area_barcode(self, obj):
        id = getattr(obj, "id")
        return format_html("<a href= '%s' >Download Barcode</a>" % (reverse('qc_barcode', args=[id])))

    download_area_barcode.short_description = 'Download Area Barcode'

    def has_delete_permission(self, request, obj=None):
        return False


class ZonePutawayUserAssignmentMappingAdmin(admin.ModelAdmin):
    list_display = ('zone', 'user', 'last_assigned_at')
    list_filter = [ZoneFilter, PutawayUserFilter]
    list_per_page = 50
    ordering = ('-zone',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class ZonePickerUserAssignmentMappingAdmin(admin.ModelAdmin):
    list_display = ('zone', 'user', 'last_assigned_at')
    list_filter = [ZoneFilter, PickerUserFilter]
    list_per_page = 50
    ordering = ('-zone',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


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
admin.site.register(WarehouseAssortment, WarehouseAssortmentAdmin)
admin.site.register(Zone, ZoneAdmin)
admin.site.register(QCArea, QCAreaAdmin)
admin.site.register(ZonePutawayUserAssignmentMapping, ZonePutawayUserAssignmentMappingAdmin)
admin.site.register(ZonePickerUserAssignmentMapping, ZonePickerUserAssignmentMappingAdmin)
