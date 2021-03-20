# python imports
import logging
import csv
from io import StringIO
# django imports
from django.contrib import admin
from django.http import HttpResponse


# app imports
from .models import AutoOrderProcessing

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

# Register your models here.
class AutoOrderProcessingAdmin(admin.ModelAdmin):
    actions = ['download_csv_for_auto_order']
    list_display = ('invoice_number', 'invoice_date', 'source_po', 'grn', 'auto_po', 'grn_warehouse',
                    'retailer_shop',)
    list_per_page = 50

    def invoice_number(self, obj):
        return obj.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.invoice_no

    def invoice_date(self, obj):
        return obj.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.created_at

    def get_queryset(self, request):
        qs = super(AutoOrderProcessingAdmin, self).get_queryset(request)
        return qs.filter(state=14).order_by('-auto_po').distinct('auto_po').select_related()

    def download_csv_for_auto_order(self, request, queryset):
        """
        :param self:
        :param request:
        :param queryset:
        :return:
        """
        f = StringIO()
        writer = csv.writer(f)
        # set the header name
        writer.writerow(["Invoice Number", "Invoice Date", "Supplier Name", "Supplier ID", "Supplier Address",
                         "GRN Number(GFDN)", "GRN Date", "PO Number(GFDN)", "SKU ID", "Product Name", "GST Rate",
                         "Delivered Qty(GRN)", "Buying Price", "Amount (Qty*Buying Price)", "CGST", "SGST", "IGST",
                         "CESS", "Discount", "TCS Amount", "Invoice Amount"])

        for query in queryset:
            # iteration for selected id from Admin Dashboard and get the instance
            for obj in query.auto_po.order_cart_mapping.order_grn_order.all():
                # get object from queryset
                for product in obj.grn_order_grn_order_product.all():
                    tax_percentage = product.product.product_gst
                    total_amount = (product.delivered_qty*product.po_product_price)
                    writer.writerow([query.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.invoice_no,
                                     query.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.created_at,
                                     query.grn_warehouse.parent_shop, query.grn_warehouse.id,
                                     query.grn_warehouse.get_shop_parent.get_shop_shipping_address,
                                     obj.grn_id, obj.grn_date, obj.order.ordered_cart.po_no, product.product.product_sku,
                                     product.product.product_name, product.product.product_gst, product.delivered_qty,
                                     product.po_product_price, total_amount,
                                     ((total_amount)*(tax_percentage/100))/2, ((total_amount)*(tax_percentage/100))/2,
                                     '',
                                     product.product.product_cess,
                                     query.cart.rt_order_cart_mapping.rt_order_order_product.all().last().order.total_discount_amount,
                                     obj.tcs_amount,
                                     query.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.invoice_amount,
                                     ])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=auto_order.csv'
        return response


    download_csv_for_auto_order.short_description = "Download CSV of Auto Order"

admin.site.register(AutoOrderProcessing, AutoOrderProcessingAdmin)
