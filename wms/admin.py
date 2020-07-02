from django.contrib import admin
from django.http import HttpResponse
from .views import bins_upload, put_away,CreatePickList
from import_export import resources
import csv
from django.contrib import messages
from .models import (Bin, InventoryType, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup, PickupBinInventory,
                     WarehouseInventory, InventoryState, WarehouseInventoryChange)
from .forms import (BinForm, InForm, PutAwayForm, PutAwayBinInventoryForm, BinInventoryForm, OutForm, PickupForm)
from django.utils.html import format_html
from barCodeGenerator import barcodeGen
from django.urls import reverse


class BinResource(resources.ModelResource):
    class Meta:
        model = Bin
        exclude = ('created_at', 'modified_at')


class BinAdmin(admin.ModelAdmin):
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
    form = InForm
    list_display = ('warehouse', 'sku', 'quantity')


class PutAwayAdmin(admin.ModelAdmin):
    form = PutAwayForm
    list_display = ('warehouse','putaway_type', 'putaway_type_id', 'sku', 'batch_id','quantity','putaway_quantity')


class PutawayBinInventoryAdmin(admin.ModelAdmin):
    form = PutAwayBinInventoryForm
    list_display = ('warehouse', 'putaway', 'bin', 'putaway_quantity', 'created_at')


class InventoryTypeAdmin(admin.ModelAdmin):
    list_display = ('inventory_type',)


class BinInventoryAdmin(admin.ModelAdmin):
    form = BinInventoryForm
    list_select_related = ('warehouse', 'sku', 'bin', 'inventory_type')
    list_display = ('batch_id','warehouse', 'sku', 'bin','inventory_type', 'quantity', 'in_stock')
    readonly_fields = ('batch_id','warehouse', 'sku', 'bin','inventory_type', 'in_stock')


class OutAdmin(admin.ModelAdmin):
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
    form = PickupForm
    list_display = ('warehouse', 'pickup_type', 'pickup_type_id', 'sku', 'quantity','pickup_quantity')
    # readonly_fields = ('quantity','pickup_quantity',)

    def download_picklist(self, obj):
        return format_html(
            "<a href= '%s' >Download Picklist</a>" %
            (reverse('create-picklist', args=[obj.pk]))
        )

    download_picklist.short_description = 'Download Picklist'

class PickupBinInventoryAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'pickup', 'batch_id', 'bin', 'pickup_quantity','created_at')
    list_select_related = ('warehouse', 'pickup', 'bin')
    readonly_fields = ('warehouse', 'pickup', 'batch_id', 'bin','created_at')


class WarehouseInventoryAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'inventory_type', 'inventory_state', 'quantity', 'in_stock', 'created_at', 'modified_at')
    list_select_related = ('warehouse', 'inventory_type', 'inventory_state', 'sku')
    readonly_fields = ('warehouse', 'sku', 'inventory_type', 'inventory_state', 'quantity', 'in_stock', 'created_at', 'modified_at')


class InventoryStateAdmin(admin.ModelAdmin):
    list_display = ('inventory_state',)
    readonly_fields = ('inventory_state',)


class WarehouseInventoryChangeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'sku', 'transaction_type', 'transaction_id', 'initial_stage', 'final_stage', 'quantity', 'created_at', 'modified_at')
    list_select_related = ('warehouse', 'sku')
    readonly_fields = ('warehouse', 'sku', 'transaction_type', 'transaction_id', 'initial_stage', 'final_stage', 'quantity', 'created_at', 'modified_at')


admin.site.register(Bin, BinAdmin)
admin.site.register(In, InAdmin)
admin.site.register(InventoryType, InventoryTypeAdmin)
admin.site.register(Putaway, PutAwayAdmin)
admin.site.register(PutawayBinInventory, PutawayBinInventoryAdmin)
admin.site.register(BinInventory, BinInventoryAdmin)
admin.site.register(Out, OutAdmin)
admin.site.register(Pickup, PickupAdmin)
admin.site.register(PickupBinInventory, PickupBinInventoryAdmin)
admin.site.register(WarehouseInventory, WarehouseInventoryAdmin)
admin.site.register(InventoryState, InventoryStateAdmin)
admin.site.register(WarehouseInventoryChange, WarehouseInventoryChangeAdmin)
