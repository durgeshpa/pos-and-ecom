# python imports
import logging
import csv
from io import StringIO
# django imports
from django.contrib import admin
from django.http import HttpResponse
from rangefilter.filter import DateTimeRangeFilter
# app imports
from .models import AutoOrderProcessing

# log info
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


# Register your models here.
class AutoOrderProcessingAdmin(admin.ModelAdmin):
    actions = ['download_csv_for_auto_order']
    list_display = ('invoice_number', 'invoice_date', 'source_po', 'grn', 'auto_po', 'auto_grn', 'order', 'cart',  'grn_warehouse',
                    'retailer_shop', 'created_at', 'updated_at',)
    list_filter = [('created_at', DateTimeRangeFilter)]
    list_per_page = 50

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    @staticmethod
    def invoice_number(obj):
        """
        auto order processing object
        """
        return obj.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.invoice_no

    @staticmethod
    def invoice_date(obj):
        """
        auto order processing object
        """
        return obj.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.created_at

    def get_queryset(self, request):
        """
        request
        """
        qs = super(AutoOrderProcessingAdmin, self).get_queryset(request)
        return qs.filter(state=14)

    def download_csv_for_auto_order(self, request, queryset):
        """
        :param self:self initialization
        :param request: request object
        :param queryset: auto order process
        :return: csv file
        """
        f = StringIO()
        writer = csv.writer(f)
        # set the header name
        writer.writerow(["Invoice Number", "Invoice Date", "Supplier Name", "Supplier ID", "Supplier Address",
                         "GRN Number(GFDN)", "GRN Date", "PO Number(GFDN)", "SKU ID", "Product Name", "GST Rate",
                         "Delivered Qty(GRN)", "Buying Price", "Amount (Qty*Buying Price)", "CGST", "SGST", "IGST",
                         "CESS", "Discount", "TCS Amount", "Invoice Amount"])
        counter = 0
        data_dict = {}
        for query in queryset:
            # get grn object from auto po source
            for grn_object in query.auto_po.order_cart_mapping.order_grn_order.all():
                # check condition if grn invoice is same or not from grn object
                if query.order.rt_order_order_product.all()[0].invoice.invoice_no == grn_object.invoice_no:
                    order_products = query.cart.rt_cart_list.all()
                    for product in grn_object.grn_order_grn_order_product.all():
                        for order_product in order_products:
                            # po cart list product is not same as grn product
                            if order_product.cart_product != product.product:
                                continue
                            tax_percentage = product.product.product_gst
                            product_qty = product.delivered_qty if product.delivered_qty else 0
                            po_product_price = product.po_product_price if product.po_product_price else 0
                            total_amount = (product_qty * po_product_price)
                            counter += 1
                            if product.product.product_sku in data_dict:
                                data_dict_item = data_dict[grn_object.grn_id + product.product.product_sku]
                                data_dict_item[11] += product.delivered_qty
                                data_dict_item[13] = data_dict_item[11] * data_dict_item[12]
                                data_dict_item[14] = round(
                                    (data_dict_item[13] * tax_percentage / (100 + tax_percentage)) / 2, 2)
                                data_dict_item[15] = round(
                                    (data_dict_item[13] * tax_percentage / (100 + tax_percentage)) / 2, 22
                                    )
                                data_dict[grn_object.grn_id + product.product.product_sku] = data_dict_item
                                continue
                            # create dictionary which contains list object
                            data_dict[grn_object.grn_id + product.product.product_sku] = [
                                query.cart.rt_order_cart_mapping.rt_order_order_product.all()[0].invoice.invoice_no,
                                (query.cart.rt_order_cart_mapping.rt_order_order_product.all(
                                )[0].invoice.created_at.date()),
                                query.auto_po.supplier_name.company_name, query.auto_po.supplier_name.id,
                                query.auto_po.supplier_name.address_line1 + " " + query.auto_po.supplier_name.pincode
                                + " " +
                                query.auto_po.supplier_name.city.city_name + " " +
                                query.auto_po.supplier_name.state.state_name,
                                grn_object.grn_id, grn_object.grn_date, grn_object.order.ordered_cart.po_no,
                                product.product.product_sku,
                                product.product.product_name, product.product.product_gst, product.delivered_qty,
                                product.po_product_price, total_amount,
                                round((total_amount * tax_percentage / (100 + tax_percentage)) / 2, 2),
                                round((total_amount * tax_percentage / (100 + tax_percentage)) / 2, 2),
                                '',
                                product.product.product_cess,
                                (query.cart.rt_order_cart_mapping.rt_order_order_product.all().last(
                                ).order.total_discount_amount),
                                grn_object.tcs_amount,
                                grn_object.invoice_amount
                                ]
        # iterate to write data in csv file
        for key, value in data_dict.items():
            writer.writerow(value)
        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=auto_po_invoice.csv'
        return response

    download_csv_for_auto_order.short_description = "Download CSV of Auto Order"


# register admin
admin.site.register(AutoOrderProcessing, AutoOrderProcessingAdmin)
