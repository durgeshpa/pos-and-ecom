from django.contrib import admin
from django.conf.urls import url

from pos.models import RetailerProduct, RetailerProductImage, Payment, UserMappedShop
from pos.views import upload_retailer_products_list, download_retailer_products_list_form_view, \
    DownloadRetailerCatalogue, RetailerCatalogueSampleFile, RetailerProductMultiImageUpload
from pos.forms import RetailerProductsForm
from marketing.filters import UserFilter


class RetailerProductImageAdmin(admin.TabularInline):
    model = RetailerProductImage
    fields = ('image', 'image_thumbnail',)
    readonly_fields = ('image', 'image_thumbnail',)

    def has_add_permission(self, request, obj=None):
        return False


class RetailerProductAdmin(admin.ModelAdmin):
    form = RetailerProductsForm
    list_display = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code', 'linked_product', 'description',
                    'sku_type', 'status', 'created_at', 'modified_at')
    fields = ('shop', 'linked_product', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
              'description', 'sku_type', 'status', 'created_at', 'modified_at')
    readonly_fields = ('shop', 'sku', 'name', 'mrp', 'selling_price', 'product_ean_code',
                       'description', 'sku_type', 'status', 'created_at', 'modified_at')
    list_per_page = 50
    inlines = [RetailerProductImageAdmin, ]

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj.linked_product:
            return self.readonly_fields + ('linked_product',)
        return self.readonly_fields

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

            url(r'^retailer_product_multiple_images_upload/$',
                self.admin_site.admin_view(RetailerProductMultiImageUpload.as_view()),
                name='retailer_product_multiple_images_upload'),

        ] + urls
        return urls


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment_mode', 'paid_by', 'processed_by', 'created_at')
    
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserMappedShopAdmin(admin.ModelAdmin):
    list_display = ('shop', 'user')
    list_filter = [UserFilter]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


admin.site.register(RetailerProduct, RetailerProductAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(RetailerProductImage)
admin.site.register(UserMappedShop, UserMappedShopAdmin)
