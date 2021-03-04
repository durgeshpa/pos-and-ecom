from django.contrib import admin
from django.conf.urls import url

from pos.models import RetailerProduct, RetailerProductImage
from pos.views import upload_retailer_products_list, \
    download_retailer_products_list_form_view, DownloadRetailerCatalogue, RetailerCatalogueSampleFile


class RetailerProductAdmin(admin.ModelAdmin):
    list_display = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'linked_product', 'description', 'sku_type', 'status', 'created_at', 'modified_at')
    fields = ('shop', 'linked_product', 'sku', 'name', 'mrp', 'selling_price', 'description', 'sku_type', 'status', 'created_at', 'modified_at')
    readonly_fields = ('shop', 'linked_product', 'sku_type', 'created_at', 'modified_at')
    list_per_page = 50

    change_list_template = 'admin/pos/pos_change_list.html'

    def get_urls(self):
        """" Download & Upload(For Creating OR Updating Bulk Products) Retailer Product CSV"""
        urls = super(RetailerProductAdmin, self).get_urls()
        urls = [
            url(r'retailer_products_csv_download_form',
                self.admin_site.admin_view(download_retailer_products_list_form_view),
                name="retailer_products_csv_download_form"),

           url(r'retailer_products_csv_download',
               self.admin_site.admin_view(DownloadRetailerCatalogue),
               name="retailer_products_csv_download"),

           url(r'retailer_products_csv_upload',
               self.admin_site.admin_view(upload_retailer_products_list),
               name="retailer_products_csv_upload"),

           url(r'download_sample_file',
               self.admin_site.admin_view(RetailerCatalogueSampleFile),
               name="download_sample_file"),

        ] + urls
        return urls


admin.site.register(RetailerProduct, RetailerProductAdmin)
admin.site.register(RetailerProductImage)
