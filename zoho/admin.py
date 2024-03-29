from dal_admin_filters import AutocompleteFilter
from django.contrib import admin
from .models import ZohoFileUpload, ZohoInvoice, ZohoInvoiceItem, ZohoCreditNote, ZohoCreditNoteItem,ZohoCustomers

# Register your models here.
from .views import bulk_zoho_invoice_file_upload, bulk_zoho_credit_note_file_upload, bulk_upload_zoho_customers_file_upload

class UserFilter(AutocompleteFilter):
    title = 'Created By'
    field_name = 'created_by'
    autocomplete_url = 'zoho-users-autocomplete'


class ZohoFileUploadAdmin(admin.ModelAdmin):
    list_display = ['file', 'upload_type', 'created_by', 'updated_by', 'created_at', 'updated_at']
    list_filter = ['upload_type', 'created_at', 'updated_at']
    ordering = ('-created_at',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
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

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class ZohoCreditNoteItemAdmin(admin.TabularInline):
    model = ZohoCreditNoteItem

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass

class ZohoCustomersAdmin(admin.ModelAdmin):
    list_display = ['created_by', 'created_time', 'last_modified_time', 'display_name', 'company_name', 'salutation', 'first_name', 'last_name', 'phone',
             'currency_code', 'notes', 'website',
             'status', 'opening_balance', 'exchange_rate', 'branch_id', 'branch_name', 'credit_limit',
             'customer_sub_type', 'billing_attention', 'billing_address', 'billing_street2', 'billing_city',
             'billing_state', 'billing_country', 'billing_code', 'billing_phone', 'billing_fax', 'shipping_attention',
             'shipping_address', 'shipping_street2', 'shipping_city', 'shipping_state', 'shipping_country', 'shipping_code',
             'shipping_phone', 'shipping_fax', 'skype_identity', 'facebook', 'twitter', 'department', 'designation', 'price_list',
             'payment_team', 'payment_team_labs', 'gst_treatment', 'gst_identification_number', 'pan_number', 'last_sync_time',
             'owner_name',
             'primary_contact_id', 'email_id', 'mobile_phone', 'contact_id', 'contact_name', 'contact_type', 'place_of_contact',
             'place_of_contact_with_state_code',
             'taxable', 'tax_name', 'tax_percentage', 'exemption_reason', 'contact_address_id', 'source',]

    list_filter = ['status']
    search_fields = ['display_name']
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

class ZohoInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_id', 'invoice_number', 'invoice_status', 'invoice_date', 'customer_name',
                    'shipping_phone_number', 'shipping_bill', 'shipping_bill_date', 'shipping_bill_total',
                    'subtotal', 'total', 'balance', 'created_by', 'updated_by', 'created_at', 'updated_at']
    list_filter = ['invoice_status', UserFilter]
    inlines = [ZohoInvoiceItemAdmin, ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


class ZohoCreditNoteAdmin(admin.ModelAdmin):
    list_display = ['creditnotes_id', 'credit_note_date', 'credit_note_number', 'credit_note_status',
                    'reference', 'associated_invoice_number', 'associated_invoice_date', 'reason',
                    'created_by', 'updated_by', 'created_at', 'updated_at']
    list_filter = [UserFilter,]
    inlines = [ZohoCreditNoteItemAdmin, ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


admin.site.register(ZohoFileUpload, ZohoFileUploadAdmin)
admin.site.register(ZohoInvoice, ZohoInvoiceAdmin)
admin.site.register(ZohoCreditNote, ZohoCreditNoteAdmin)
admin.site.register(ZohoCustomers, ZohoCustomersAdmin)

