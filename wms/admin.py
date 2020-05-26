from django.contrib import admin
from django.http import HttpResponse
from .views import bins_upload
from import_export import resources
import csv
from django.contrib import messages
from .models import Bin, InventoryType

class BinResource(resources.ModelResource):
    class Meta:
        model = Bin
        exclude = ('created_at', 'modified_at')


class WMSBIN:
    def export_as_csv_forbins(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        return response
    export_as_csv_forbins.short_description = "Download CSV of selected bins"


class BinAdmin(admin.ModelAdmin, WMSBIN):
    resource_class = BinResource
    actions = ['export_as_csv_forbins',]
    list_display = ('warehouse', 'bin_id', 'bin_type', 'created_at', 'modified_at', 'is_active')
    readonly_fields = ['bin_barcode','barcode_image','decoded_barcode',]

    def get_urls(self):
        from django.conf.urls import url
        urls = super(BinAdmin, self).get_urls()
        urls = [
            url(
                r'^upload-csv/$',
                self.admin_site.admin_view(bins_upload),
                name="bins-upload"
            )] + urls
        return urls



admin.site.register(Bin, BinAdmin)
admin.site.register(InventoryType)