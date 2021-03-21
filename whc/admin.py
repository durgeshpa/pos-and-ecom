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
    list_display = ('invoice_number', 'invoice_date', 'source_po', 'auto_po', 'order', 'cart', 'grn_warehouse',
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
                    amount_exclude_tax = (total_amount)/(1+tax_percentage/100)
                    tax_amount = total_amount - amount_exclude_tax
                    if product.delivered_qty == 0:
                        continue
                    else:
                        writer.writerow([str(query.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.invoice_no),
                                         str(query.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.created_at),
                                         str(query.auto_po.supplier_name.company_name), str(query.auto_po.supplier_name_id),
                                         str(query.auto_po.supplier_name.address_line1),
                                         str(obj.grn_id), str(obj.grn_date), str(obj.order.ordered_cart.po_no), str(product.product.product_sku),
                                         str(product.product.product_name), str(product.product.product_gst), str(product.delivered_qty),
                                         str(product.po_product_price), str(total_amount),
                                         "{:.1f}".format((tax_amount/2)), "{:.1f}".format((tax_amount/2)),
                                         '',
                                         str(product.product.product_cess),
                                         str(query.cart.rt_order_cart_mapping.rt_order_order_product.all().last().order.total_discount_amount),
                                         str(obj.tcs_amount),
                                         str(obj.invoice_amount),
                                         ])

        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=auto_order.csv'
        return response


    download_csv_for_auto_order.short_description = "Download CSV of Auto Order"

admin.site.register(AutoOrderProcessing, AutoOrderProcessingAdmin)
