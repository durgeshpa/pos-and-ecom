from django.contrib import admin
from .models import ZohoFileUpload, ZohoInvoice, ZohoInvoiceItem

# Register your models here.
from .views import bulk_zoho_invoice_file_upload, bulk_zoho_credit_note_file_upload, bulk_upload_zoho_customers_file_upload

class ZohoFileUploadAdmin(admin.ModelAdmin):
    list_display = ['file', 'upload_type', 'created_by', 'updated_by', 'created_at', 'updated_at']
    list_filter = ['upload_type', 'created_at', 'updated_at']
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request):
        return False

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ZohoFileUploadAdmin, self).get_urls()
        urls = [
                   url(
                       r'^bulk-upload-invoices/$',
                       self.admin_site.admin_view(bulk_zoho_invoice_file_upload),
                       name="bulk-upload-invoices"
                   ),
                   url(
                       r'^bulk-upload-credit-note/$',
                       self.admin_site.admin_view(bulk_zoho_credit_note_file_upload),
                       name="bulk-upload-credit-note"
                   ),
                   url(
                       r'^bulk-upload-ZohoCustomers/$',
                       self.admin_site.admin_view(bulk_upload_zoho_customers_file_upload),
                       name="bulk-upload-ZohoCustomers"
                   )
               ] + urls
        return urls


class ZohoInvoiceItemAdmin(admin.TabularInline):
    model = ZohoInvoiceItem

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    class Media:
        pass


class ZohoInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_date', 'invoice_id', 'invoice_number', 'invoice_status']
    inlines = [ZohoInvoiceItemAdmin, ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(ZohoFileUpload, ZohoFileUploadAdmin)
admin.site.register(ZohoInvoice, ZohoInvoiceAdmin)

