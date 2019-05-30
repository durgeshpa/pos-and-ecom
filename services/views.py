import requests
from PIL import Image
import PIL

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse, Http404
from django.conf import settings
from retailer_to_sp.models import Order, OrderedProductMapping
from shops.models import Shop, ParentRetailerMapping
from django.db.models import Sum
import json
import csv
from rest_framework import permissions, authentication
from .forms import SalesReportForm, OrderReportForm, GRNReportForm, MasterReportForm
from django.views import View
from products.models import Product, ProductPrice, ProductOption,ProductImage, ProductTaxMapping, Tax
from .models import OrderReports,GRNReports, MasterReports
from gram_to_brand.models import Order as PurchaseOrder
# Create your views here.
class SalesReport(APIView):
    permission_classes = (AllowAny,)

    def get_sales_report(self, shop_id, start_date, end_date):
        seller_shop = Shop.objects.get(pk=shop_id)
        orders = Order.objects.using('readonly').filter(seller_shop = seller_shop).select_related('ordered_cart').prefetch_related('ordered_cart__rt_cart_list')
        if start_date:
            orders = orders.using('readonly').filter(created_at__gte = start_date)
        if end_date:
            orders = orders.using('readonly').filter(created_at__lte = end_date)
        ordered_items = {}
        for order in orders:
            order_shipments = OrderedProductMapping.objects.using('readonly').filter(
                ordered_product__order = order
                )
            for cart_product_mapping in order.ordered_cart.rt_cart_list.all():
                product = cart_product_mapping.cart_product
                product_id = cart_product_mapping.cart_product.id
                product_name = cart_product_mapping.cart_product.product_name
                product_sku = cart_product_mapping.cart_product.product_sku
                product_brand = cart_product_mapping.cart_product.product_brand.brand_name
                ordered_qty = cart_product_mapping.no_of_pieces
                all_tax_list = cart_product_mapping.cart_product.product_pro_tax

                product_shipments = order_shipments.filter(product=product)
                product_shipments = product_shipments.aggregate(Sum('delivered_qty'))['delivered_qty__sum']
                if not product_shipments:
                    product_shipments = 0
                tax_sum = 0
                if all_tax_list.exists():
                    for tax in all_tax_list.using('readonly').all():
                        tax_sum = float(tax_sum) + float(tax.tax.tax_percentage)
                    tax_sum = round(tax_sum, 2)
                    get_tax_val = tax_sum / 100
                product_price_to_retailer = cart_product_mapping.cart_product_price.price_to_retailer
                ordered_amount = round((float(product_price_to_retailer)*int(ordered_qty)) / (float(get_tax_val) + 1), 2)
                ordered_tax_amount = round((float(ordered_amount) * float(get_tax_val)), 2)
                delivered_amount = round((float(product_price_to_retailer)*int(product_shipments)) / (float(get_tax_val) + 1), 2)
                delivered_tax_amount = round((float(delivered_amount) * float(get_tax_val)), 2)
                if product.product_gf_code in ordered_items:
                    ordered_items[product.product_gf_code]['ordered_qty'] += ordered_qty
                    ordered_items[product.product_gf_code]['ordered_amount'] += ordered_amount
                    ordered_items[product.product_gf_code]['ordered_tax_amount'] += ordered_tax_amount
                    ordered_items[product.product_gf_code]['delivered_qty'] += product_shipments
                    ordered_items[product.product_gf_code]['delivered_amount'] += delivered_amount
                    ordered_items[product.product_gf_code]['delivered_tax_amount'] += delivered_tax_amount
                else:
                    ordered_items[product.product_gf_code] = {'product_sku':product_sku, 'product_id':product_id, 'product_name':product_name,'product_brand':product_brand,'ordered_qty':ordered_qty, 'delivered_qty':product_shipments, 'ordered_amount':ordered_amount, 'ordered_tax_amount':ordered_tax_amount, 'delivered_amount':delivered_amount, 'delivered_tax_amount':delivered_tax_amount}

        data = ordered_items
        return data

    def get(self, *args, **kwargs):
        from django.http import HttpResponse
        from django.contrib import messages
        shop_id = self.request.GET.get('shop')
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        if end_date and end_date < start_date:
            messages.error(self.request, 'End date cannot be less than the start date')
            return render(
                self.request,
                'admin/services/sales-report.html',
                {'form': SalesReportForm(user=None, initial=self.request.GET)}
            )
        data = self.get_sales_report(shop_id, start_date, end_date)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['GF Code', 'ID', 'SKU', 'Product Name', 'Brand', 'Ordered Qty', 'Delivered Qty', 'Ordered Amount', 'Ordered Tax Amount', 'Delivered Amount', 'Delivered Tax Amount'])
        for k,v in data.items():
            writer.writerow([k, v['product_id'], v['product_sku'], v['product_name'], v['product_brand'], v['ordered_qty'], v['delivered_qty'], v['ordered_amount'], v['ordered_tax_amount'],  v['delivered_amount'], v['delivered_tax_amount']])

        return response

class SalesReportFormView(View):
    def get(self, request):
        form = SalesReportForm(user=request.user)
        return render(
            self.request,
            'admin/services/sales-report.html',
            {'form': form}
        )

class OrderReport(APIView):
    permission_classes = (AllowAny,)

    def get_order_report(self, shop_id, start_date, end_date):
        seller_shop = Shop.objects.get(pk=shop_id)
        orders = Order.objects.filter(seller_shop = seller_shop)
        if start_date:
            orders = orders.filter(created_at__gte = start_date)
        if end_date:
            orders = orders.filter(created_at__lte = end_date)
        order_details = {}
        i=0
        for order in orders:
            for shipment in order.rt_order_order_product.all():
                for products in shipment.rt_order_product_order_product_mapping.all():
                    i += 1
                    product_id = products.product.id
                    product_name = products.product.product_name
                    product_brand = products.product.product_brand
                    product_mrp = products.product.product_pro_price.get(status=True, shop = seller_shop).mrp
                    product_value_tax_included = products.product.product_pro_price.get(status=True, shop = seller_shop).price_to_retailer
                    if products.product.product_pro_tax.filter(tax__tax_type ='gst').exists():
                        product_gst = products.product.product_pro_tax.get(tax__tax_type ='gst')
                    if order.shipping_address.state == order.seller_shop.shop_name_address_mapping.get(address_type='shipping').state:
                        product_cgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_sgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_igst = ''
                    else:
                        product_cgst = ''
                        product_sgst = ''
                        product_igst = (float(product_gst.tax.tax_percentage))
                    if products.product.product_pro_tax.filter(tax__tax_type ='cess').exists():
                        product_cess = products.product.product_pro_tax.get(tax__tax_type ='cess').tax.tax_percentage
                    else:
                        product_cess = ''
                    order_id = order.order_no
                    pin_code = order.shipping_address.pincode
                    order_status = order.get_order_status_display()
                    order_date = order.created_at
                    order_by = order.ordered_by
                    retailer_id = order.ordered_by.id
                    order_invoice = shipment.invoice_no
                    invoice_date = shipment.created_at
                    invoice_status = shipment.get_shipment_status_display()
                    ordered_sku_pieces = products.ordered_qty
                    shipped_sku_pieces = products.shipped_qty
                    delivered_sku_pieces = products.delivered_qty
                    returned_sku_pieces = products.returned_qty
                    damaged_sku_pieces = products.damaged_qty
                    sales_person_name = ''
                    order_type =''
                    campaign_name =''
                    discount = ''
                    OrderReports.objects.using('gfanalytics').create(order_invoice = order_invoice, invoice_date = invoice_date, invoice_status = invoice_status, order_id = order_id,  order_status = order_status, order_date = order_date, order_by = order_by, retailer_id = retailer_id, pin_code = pin_code, product_id = product_id, product_name = product_name, product_brand = product_brand, product_mrp = product_mrp, product_value_tax_included = product_value_tax_included, ordered_sku_pieces = ordered_sku_pieces,  shipped_sku_pieces = shipped_sku_pieces, delivered_sku_pieces = delivered_sku_pieces, returned_sku_pieces = returned_sku_pieces, damaged_sku_pieces = damaged_sku_pieces, product_cgst = product_cgst, product_sgst = product_sgst, product_igst = product_igst, product_cess = product_cess, sales_person_name = sales_person_name, order_type = order_type, campaign_name = campaign_name, discount = discount)
                    order_details[i] = {'order_invoice':order_invoice, 'invoice_date':invoice_date, 'invoice_status':invoice_status, 'order_id':order_id,  'order_status':order_status, 'order_date':order_date, 'order_by':order_by, 'retailer_id':retailer_id, 'pin_code':pin_code, 'product_id':product_id, 'product_name':product_name, 'product_brand':product_brand, 'product_mrp':product_mrp, 'product_value_tax_included':product_value_tax_included, 'ordered_sku_pieces':ordered_sku_pieces, 'shipped_sku_pieces':shipped_sku_pieces, 'delivered_sku_pieces':delivered_sku_pieces, 'returned_sku_pieces':returned_sku_pieces, 'damaged_sku_pieces':damaged_sku_pieces, 'product_cgst':product_cgst, 'product_sgst':product_sgst, 'product_igst':product_igst, 'product_cess':product_cess, 'sales_person_name':sales_person_name, 'order_type':order_type, 'campaign_name':campaign_name, 'discount':discount}

        data = order_details
        return data

    def get(self, *args, **kwargs):
        from django.http import HttpResponse
        from django.contrib import messages

        shop_id = self.request.GET.get('shop')
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        if end_date and end_date < start_date:
            messages.error(self.request, 'End date cannot be less than the start date')
            return render(
                self.request,
                'admin/services/order-report.html',
                {'form': OrderReportForm(user=None, initial=self.request.GET)}
            )
        data = self.get_order_report(shop_id, start_date, end_date)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="order-mis-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['S.No.', 'Invoice Id', 'Invoice Date', 'Invoice Status', 'Order Id', 'Order Status', 'Order Date', 'Retailer Name/Contact No.', 'Retailer Id', 'PinCode', 'Product Id', 'Product Name', 'Product Brand', 'Product MRP' ,'Product Value including tax', 'Ordered SKU Pieces', 'Shipped SKU Pieces', 'Delivered SKU Pieces', 'Returned SKU Pieces', 'Damaged SKU Pieces', 'CGST %', 'SGST %', 'IGST %', 'Cess %', 'Sales Person Name', 'Order Type (Organic / Through Sales Person)', 'Campaign Name', 'Discount %'])
        for k,v in data.items():
            writer.writerow([k, v['order_invoice'], v['invoice_date'], v['invoice_status'], v['order_id'], v['order_status'], v['order_date'], v['order_by'], v['retailer_id'], v['pin_code'], v['product_id'], v['product_name'], v['product_brand'], v['product_mrp'], v['product_value_tax_included'], v['ordered_sku_pieces'], v['shipped_sku_pieces'], v['delivered_sku_pieces'], v['returned_sku_pieces'], v['damaged_sku_pieces'], v['product_cgst'], v['product_sgst'], v['product_igst'], v['product_cess'], v['sales_person_name'], v['order_type'], v['campaign_name'], v['discount']])

        return response

class OrderReportFormView(View):
    def get(self, request):
        form = OrderReportForm(user=request.user)
        return render(
            self.request,
            'admin/services/order-report.html',
            {'form': form}
        )


class GRNReport(APIView):
    permission_classes = (AllowAny,)

    def get_grn_report(self, shop_id, start_date, end_date):
        buyer_shop = Shop.objects.get(pk=shop_id)
        orders = PurchaseOrder.objects.filter(ordered_cart__gf_shipping_address__shop_name = buyer_shop)
        if start_date:
            orders = orders.filter(created_at__gte = start_date)
        if end_date:
            orders = orders.filter(created_at__lte = end_date)
        grn_details = {}
        i=0
        for order in orders:
            for grns in order.order_grn_order.all():
                for products in grns.grn_order_grn_order_product.all():
                    i += 1
                    product_id = products.product.id
                    product_name = products.product.product_name
                    product_brand = products.product.product_brand
                    if products.product.product_pro_price.filter(status=True, shop = buyer_shop).exists():
                        product_mrp = products.product.product_pro_price.get(status=True, shop = buyer_shop).mrp
                    else:
                        product_mrp = ''
                    gram_to_brand_price = grns.grn_order_grn_order_product.filter(product = products.product).last().po_product_price
                    #product_value_tax_included = products.product.product_pro_price.get(status=True, shop = buyer_shop).price_to_retailer
                    if products.product.product_pro_tax.filter(tax__tax_type ='gst').exists():
                        product_gst = products.product.product_pro_tax.get(tax__tax_type ='gst')
                    if order.ordered_cart.supplier_state == order.ordered_cart.gf_shipping_address.state:
                        product_cgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_sgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_igst = ''
                    else:
                        product_cgst = ''
                        product_sgst = ''
                        product_igst = (float(product_gst.tax.tax_percentage))
                    if products.product.product_pro_tax.filter(tax__tax_type ='cess').exists():
                        product_cess = products.product.product_pro_tax.get(tax__tax_type ='cess').tax.tax_percentage
                    else:
                        product_cess = ''
                    po_no = order.order_no
                    po_date = order.created_at
                    po_status = order.ordered_cart.get_po_status_display()
                    vendor_name = order.ordered_cart.supplier_name
                    vendor_id = order.ordered_cart.supplier_name.id
                    shipping_address = order.ordered_cart.gf_shipping_address.address_line1
                    category_manager = ''
                    manufacture_date = grns.grn_order_grn_order_product.get(product = products.product).manufacture_date
                    expiry_date = grns.grn_order_grn_order_product.get(product = products.product).expiry_date
                    po_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).po_product_quantity
                    discount = ''
                    grn_id = grns.grn_id
                    grn_date = grns.created_at
                    grn_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty
                    invoice_item_gross_value = (grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty) * (gram_to_brand_price)
                    delivered_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).delivered_qty
                    returned_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).returned_qty
                    dn_number = ''
                    dn_value_basic =''
                    GRNReports.objects.using('gfanalytics').create(po_no = po_no, po_date = po_date, po_status = po_status, vendor_name = vendor_name,  vendor_id = vendor_id, shipping_address = shipping_address, category_manager = category_manager, product_id = product_id, product_name = product_name, product_brand = product_brand, manufacture_date = manufacture_date, expiry_date = expiry_date, po_sku_pieces = po_sku_pieces, product_mrp = product_mrp, discount = discount,  gram_to_brand_price = gram_to_brand_price, grn_id = grn_id, grn_date = grn_date, grn_sku_pieces = grn_sku_pieces, product_cgst = product_cgst, product_sgst = product_sgst, product_igst = product_igst, product_cess = product_cess, invoice_item_gross_value = invoice_item_gross_value, delivered_sku_pieces = delivered_sku_pieces, returned_sku_pieces = returned_sku_pieces, dn_number = dn_number, dn_value_basic = dn_value_basic)
                    grn_details[i] = { 'po_no':po_no, 'po_date':po_date, 'po_status':po_status, 'vendor_name':vendor_name, 'vendor_id':vendor_id, 'shipping_address':shipping_address, 'category_manager':category_manager, 'product_id':product_id, 'product_name':product_name, 'product_brand':product_brand, 'manufacture_date':manufacture_date, 'expiry_date':expiry_date, 'po_sku_pieces':po_sku_pieces, 'product_mrp':product_mrp, 'discount':discount, 'gram_to_brand_price':gram_to_brand_price, 'grn_id':grn_id, 'grn_date':grn_date, 'grn_sku_pieces':grn_sku_pieces, 'product_cgst':product_cgst, 'product_sgst':product_sgst, 'product_igst':product_igst, 'product_cess':product_cess, 'invoice_item_gross_value':invoice_item_gross_value, 'delivered_sku_pieces':delivered_sku_pieces, 'returned_sku_pieces':returned_sku_pieces, 'dn_number':dn_number, 'dn_value_basic':dn_value_basic}

        data = grn_details
        return data

    def get(self, *args, **kwargs):
        from django.http import HttpResponse
        from django.contrib import messages

        shop_id = self.request.GET.get('shop')
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        if end_date and end_date < start_date:
            messages.error(self.request, 'End date cannot be less than the start date')
            return render(
                self.request,
                'admin/services/grn-report.html',
                {'form': GRNReportForm(user=None, initial=self.request.GET)}
            )
        data = self.get_grn_report(shop_id, start_date, end_date)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="grn-mis-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['S.No.', 'PO No.', 'PO Date', 'PO Status', 'Vendor Name', 'Vendor Id', 'Shipping Address', 'Category Manager', 'Product Id', 'Product Name', 'Product Brand', 'Manufacture Date', 'Expiry Date', 'PO SKU Pieces', 'Product MRP', 'Gram to Brand Price', 'Discount %', 'GRN ID', 'GRN Date', 'Invoice SKU Pieces', 'CGST', 'SGST', 'IGST', 'CESS', 'Invoice Item Gross value', 'Delivered SKU Pieces', 'Returned SKU Pieces', 'DN Number', 'DN value (Basic)'])
        for k,v in data.items():
            writer.writerow([k, v['po_no'], v['po_date'], v['po_status'], v['vendor_name'], v['vendor_id'],  v['shipping_address'], v['category_manager'], v['product_id'], v['product_name'], v['product_brand'], v['manufacture_date'], v['expiry_date'], v['po_sku_pieces'], v['product_mrp'], v['gram_to_brand_price'], v['discount'], v['grn_id'], v['grn_date'], v['grn_sku_pieces'], v['product_cgst'], v['product_sgst'], v['product_igst'], v['product_cess'], v['invoice_item_gross_value'], v['delivered_sku_pieces'], v['returned_sku_pieces'], v['dn_number'], v['dn_value_basic']])

        return response

class GRNReportFormView(View):
    def get(self, request):
        form = GRNReportForm(user=request.user)
        return render(
            self.request,
            'admin/services/grn-report.html',
            {'form': form}
        )


class MasterReport(APIView):
    permission_classes = (AllowAny,)

    def get_master_report(self, shop_id):
        shop = Shop.objects.get(pk=shop_id)
        product_prices = ProductPrice.objects.filter(shop=shop, status=True)
        products_list = {}
        i=0
        for products in product_prices:
            i+=1
            product = products.product
            mrp = products.mrp
            price_to_retailer = products.price_to_retailer
            product_gf_code = products.product.product_gf_code
            product_ean_code = products.product.product_ean_code
            product_brand = products.product.product_brand
            product_subbrand = ''
            product_category = ''
            tax_gst_percentage = 0
            tax_cess_percentage = 0
            tax_surcharge_percentage = 0
            for tax in products.product.product_pro_tax.all():
                if tax.tax.tax_type == 'gst':
                    tax_gst_percentage = tax.tax.tax_percentage
                elif tax.tax.tax_type == 'cess':
                    tax_cess_percentage = tax.tax.tax_percentage
                elif tax.tax.tax_type == 'surcharge':
                    tax_surcharge_percentage = tax.tax.tax_percentage
            pack_size = products.product.product_inner_case_size
            case_size = products.product.product_case_size
            hsn_code = products.product.product_hsn
            product_id = products.product.id
            sku_code = products.product.product_sku
            short_description = products.product.product_short_description
            long_description = products.product.product_long_description
            MasterReports.objects.using('gfanalytics').create(product = product, mrp = mrp, price_to_retailer = price_to_retailer, product_gf_code = product_gf_code,  product_brand = product_brand, product_subbrand = product_subbrand, product_category = product_category, tax_gst_percentage = tax_gst_percentage, tax_cess_percentage = tax_cess_percentage, tax_surcharge_percentage = tax_surcharge_percentage, pack_size = pack_size, case_size = case_size, hsn_code = hsn_code, product_id = product_id, sku_code = sku_code,  short_description = short_description, long_description = long_description)

            products_list[i] = {'product':product, 'mrp':mrp, 'price_to_retailer':price_to_retailer, 'product_gf_code':product_gf_code, 'product_brand':product_brand, 'product_subbrand':product_subbrand, 'product_category':product_category, 'tax_gst_percentage':tax_gst_percentage, 'tax_cess_percentage':tax_cess_percentage, 'tax_surcharge_percentage':tax_surcharge_percentage, 'pack_size':pack_size, 'case_size':case_size, 'hsn_code':hsn_code, 'product_id':product_id, 'sku_code':sku_code, 'short_description':short_description, 'long_description':long_description}
        data = products_list
        return data

    def get(self, *args, **kwargs):
        from django.http import HttpResponse
        from django.contrib import messages

        shop_id = self.request.GET.get('shop')
        data = self.get_master_report(shop_id)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="master-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['S.No', 'Product Name', 'MRP', 'PTR', 'GF Code', 'Brand', 'Subbrand', 'Category', 'GST %', 'CESS %', 'Surcharge %', 'Pack Size', 'Case Size', 'HSN', 'Product ID', 'SKU Code', 'Short Desc.', 'Long Desc.'])
        for k,v in data.items():
            writer.writerow([k, v['product'], v['mrp'], v['price_to_retailer'], v['product_gf_code'], v['product_brand'], v['product_subbrand'], v['product_category'], v['tax_gst_percentage'], v['tax_cess_percentage'], v['tax_surcharge_percentage'], v['pack_size'], v['case_size'], v['hsn_code'],  v['product_id'], v['sku_code'], v['short_description'], v['long_description']])

        return response

class MasterReportFormView(View):
    def get(self, request):
        form = MasterReportForm(user=request.user)
        return render(
            self.request,
            'admin/services/master-report.html',
            {'form': form}
        )

class RetailerProfileReport(APIView):
    permission_classes = (AllowAny,)

    def get_master_report(self, shop_id):
        shop = Shop.objects.get(pk=shop_id)
        retailers = ParentRetailerMapping.objects.filter(parent = shop)
        retailers_list = {}
        i=0
        for retailer in retailers:
            i+=1
            retailer_id = retailer.retailer.shop_owner.id
            retailer_name = retailer.retailer.shop_owner.first_name
            retailer_type = retailer.retailer.shop_type.shop_type
            retailer_phone_number = retailer.retailer.shop_owner.phone_number
            for address in m.retailer.shop_name_address_mapping.all():
                retailer_location = address.address_line1
                retailer_pincode = address.pincode
            service_partner = shop.shop_name
            service_partner_id = shop.id
            service_partner_contact = shop.shop_owner.phone_number
            sales_manager = ''
            sales_manager_contact = ''
            bda_name = ''
            bda_number = ''

        data = retailers_list
        return data

    def get(self, *args, **kwargs):
        from django.http import HttpResponse
        from django.contrib import messages

        shop_id = self.request.GET.get('shop')
        data = self.get_master_report(shop_id)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="master-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['S.No', 'Product Name', 'MRP', 'PTR', 'GF Code', 'Brand', 'Subbrand', 'Category', 'GST %', 'CESS %', 'Surcharge %', 'Pack Size', 'Case Size', 'HSN', 'Product ID', 'SKU Code', 'Short Desc.', 'Long Desc.'])
        for k,v in data.items():
            writer.writerow([k, v['product'], v['mrp'], v['price_to_retailer'], v['product_gf_code'], v['product_brand'], v['product_subbrand'], v['product_category'], v['tax_gst_percentage'], v['tax_cess_percentage'], v['tax_surcharge_percentage'], v['pack_size'], v['case_size'], v['hsn_code'],  v['product_id'], v['sku_code'], v['short_description'], v['long_description']])

        return response

class RetailerReportFormView(View):
    def get(self, request):
        form = RetailerReportFormView(user=request.user)
        return render(
            self.request,
            'admin/services/master-report.html',
            {'form': form}
        )


class ResizeImage(APIView):
    permission_classes = (AllowAny,)
    def get(self,request, image_path, image_name, *args, **kwargs):
        path = "/".join(args)
        img_url = "https://{}/{}/{}".format(getattr(settings, 'AWS_S3_CUSTOM_DOMAIN_ORIG'), image_path,image_name, path)
        width = int(request.GET.get('width', '600'))
        height = request.GET.get('height', None)
        img_response = requests.get(img_url, stream=True)
        if img_response.status_code == 404:
            raise Http404("Image not found")
        content_type = img_response.headers.get('Content-Type')
        if content_type not in ['image/png', 'image/jpeg', 'image/jpg']:
            return HttpResponse(content=img_response.content, content_type=content_type)
        img_response.raw.decode_content = True
        image = Image.open(img_response.raw)

        if not height:
            height = int(image.height * width/image.width)
        image = image.resize((width,height), PIL.Image.LANCZOS)
        response = HttpResponse(content_type=content_type)
        image_type = {
            'image/png': 'PNG',
            'image/jpeg': 'JPEG',
            'image/jpg' : 'JPEG'
        }
        image.save(response, image_type[content_type])
        return response
