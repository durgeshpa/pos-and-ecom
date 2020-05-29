from django.contrib import admin
from django.http import HttpResponse
from .views import bins_upload, put_away
from import_export import resources
import csv
from django.contrib import messages
from .models import Bin, InventoryType, In, Putaway
from .forms import (BinForm, InForm, PutAwayForm)
from django.utils.html import format_html
from barCodeGenerator import barcodeGen


class BinResource(resources.ModelResource):
    class Meta:
        model = Bin
        exclude = ('created_at', 'modified_at')


class BinAdmin(admin.ModelAdmin):
    resource_class = BinResource
    actions = ['download_csv_for_bins',]
    list_display = ('warehouse', 'bin_id', 'bin_type', 'created_at', 'modified_at', 'is_active', 'download_bin_id_barcode')
    readonly_fields = ['bin_barcode','barcode_image','decoded_barcode','download_bin_id_barcode']

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


admin.site.register(Bin, BinAdmin)
admin.site.register(In, InAdmin)
admin.site.register(InventoryType)
admin.site.register(Putaway, PutAwayAdmin)