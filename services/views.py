import requests
from PIL import Image
import PIL
import datetime
from decimal import Decimal
from itertools import chain


from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.http import HttpResponse, Http404
from django.conf import settings
from retailer_to_sp.models import Order, OrderedProductMapping, CartProductMapping
from shops.models import ParentRetailerMapping
from shops.models import Shop
from wms.models import In, Out, InventoryType
from django.db.models import Sum
import csv
from .forms import InOutLedgerForm, SalesReportForm
from django.views import View
from products.models import Product, ProductPrice
from .models import RetailerReports, GRNReports, MasterReports, OrderGrnReports, OrderDetailReports, CategoryProductReports, OrderDetailReportsData, CartProductMappingData
from gram_to_brand.models import Order as PurchaseOrder
from gram_to_brand.models import GRNOrder as GRNOrder
# # Create your views here.
class SalesReport(APIView):
    permission_classes = (AllowAny,)

    def get_sales_report(self, shop_id, start_date, end_date):
        seller_shop = Shop.objects.get(pk=shop_id)
        orders = Order.objects.using('readonly').filter(seller_shop=seller_shop).exclude(order_status__in=['CANCELLED', 'DENIED'])\
            .select_related('ordered_cart').prefetch_related('ordered_cart__rt_cart_list')
        if start_date:
            orders = orders.using('readonly').filter(created_at__gte = start_date)
        if end_date:
            orders = orders.using('readonly').filter(created_at__lte = end_date)
        ordered_list=[]
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
                # shopName = seller_shop

                product_shipments = order_shipments.filter(product=product)
                product_shipments = product_shipments.aggregate(Sum('delivered_qty'))['delivered_qty__sum']
                if not product_shipments:
                    product_shipments = 0
                tax_sum, get_tax_val = 0, 0
                if all_tax_list.exists():
                    for tax in all_tax_list.using('readonly').all():
                        tax_sum = float(tax_sum) + float(tax.tax.tax_percentage)
                    tax_sum = round(tax_sum, 2)
                    get_tax_val = tax_sum / 100
                seller_shop = Shop.objects.filter(id=order.seller_shop_id).last()
                buyer_shop = Shop.objects.filter(id=order.buyer_shop_id).last()
                try:
                    product_price_to_retailer = cart_product_mapping.get_cart_product_price(seller_shop,
                                                            buyer_shop).get_per_piece_price(cart_product_mapping.qty)
                except:
                    product_price_to_retailer = 0
                ordered_amount = (Decimal(product_price_to_retailer) * Decimal(ordered_qty)) / (Decimal(get_tax_val) + 1)
                ordered_tax_amount = (ordered_amount * Decimal(get_tax_val))
                delivered_amount = float((Decimal(product_price_to_retailer) * Decimal(product_shipments)) / (Decimal(get_tax_val) + 1))
                delivered_tax_amount = float((delivered_amount * float(get_tax_val)))
                if product_sku in ordered_items:
                    ordered_items['ordered_qty'] += ordered_qty
                    ordered_items['ordered_amount'] += ordered_amount
                    ordered_items['ordered_tax_amount'] += ordered_tax_amount
                    ordered_items['delivered_qty'] += product_shipments
                    ordered_items['delivered_amount'] += delivered_amount
                    ordered_items['delivered_tax_amount'] += delivered_tax_amount
                else:
                    ordered_items = {'product_sku':product_sku, 'product_id':product_id, 'product_name':product_name,'product_brand':product_brand,'ordered_qty':ordered_qty, 'delivered_qty':product_shipments, 'ordered_amount':ordered_amount, 'ordered_tax_amount':ordered_tax_amount, 'delivered_amount':delivered_amount, 'delivered_tax_amount':delivered_tax_amount, 'seller_shop':seller_shop}
                    ordered_list.append(ordered_items)
        data = ordered_list
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
        writer.writerow(['ID', 'SKU', 'Product Name', 'Brand', 'Ordered Qty', 'Delivered Qty', 'Ordered Amount', 'Ordered Tax Amount', 'Delivered Amount', 'Delivered Tax Amount', 'Seller_shop'])
        for dic in data:
            writer.writerow([dic['product_id'], dic['product_sku'], dic['product_name'], dic['product_brand'], dic['ordered_qty'], dic['delivered_qty'], dic['ordered_amount'], dic['ordered_tax_amount'],  dic['delivered_amount'], dic['delivered_tax_amount'],dic['seller_shop']])

        return response

class SalesReportFormView(View):
    def get(self, request):
        form = SalesReportForm(user=request.user)
        return render(
            self.request,
            'admin/services/sales-report.html',
            {'form': form}
        )
seller_shop_map = {'172':'GFDN SERVICES PVT LTD (DELHI) - 7006440794','600':'GFDN SERVICES PVT LTD (NOIDA) - 9891597697'}

# class OrderReport(APIView):
#     permission_classes = (AllowAny,)
#     def get_order_report(self, shop_id, start_date, end_date):
#         seller_shop = Shop.objects.get(pk=shop_id)
#         last_modified_entry = OrderDetailReports.objects.filter(seller_shop=seller_shop_map[str(shop_id)]).latest('order_modified_at')
#         #first_modified_entry = OrderDetailReports.objects.filter(seller_shop=seller_shop_map[str(shop_id)]).order_by('order_modified_at').first()
#         #start_date = datetime.datetime.today()-datetime.timedelta(50)
#         start_date = last_modified_entry.order_modified_at
#         #end_date = first_modified_entry.order_modified_at
#         print(start_date)
#         #print(end_date)
#         orders = Order.objects.filter(seller_shop = seller_shop)
#         if start_date:
#             orders = orders.filter(modified_at__gte = start_date)
#         if end_date:
#             orders = orders.filter(modified_at__lte = end_date)
#         order_details = {}
#         i=0
#         for order in orders:
#             for shipment in order.rt_order_order_product.all():
#                 for products in shipment.rt_order_product_order_product_mapping.all():
#                     i += 1
#                     product_id = products.product.id
#                     product_name = products.product.product_name
#                     product_brand = products.product.product_brand
#                     #product_mrp = products.product.product_pro_price.get(status=True, shop = seller_shop).mrp
#                     #product_value_tax_included = products.product.product_pro_price.get(status=True, shop = seller_shop).price_to_retailer
#                     # New Price Logic
#                     product_mrp = products.product.getMRP(seller_shop.id,order.buyer_shop.id)
#                     product_value_tax_included = products.product.getRetailerPrice(seller_shop.id,order.buyer_shop.id)
#                     if products.product.product_pro_tax.filter(tax__tax_type ='gst').exists():
#                         product_gst = products.product.product_pro_tax.filter(tax__tax_type ='gst').last()
#                     if order.shipping_address.state == order.seller_shop.shop_name_address_mapping.filter(address_type='shipping').last().state:
#                         product_cgst = (float(product_gst.tax.tax_percentage)/2.0)
#                         product_sgst = (float(product_gst.tax.tax_percentage)/2.0)
#                         product_igst = ''
#                     else:
#                         product_cgst = ''
#                         product_sgst = ''
#                         product_igst = (float(product_gst.tax.tax_percentage))
#                     if products.product.product_pro_tax.filter(tax__tax_type ='cess').exists():
#                         product_cess = products.product.product_pro_tax.filter(tax__tax_type ='cess').last().tax.tax_percentage
#                     else:
#                         product_cess = ''
#                     invoice_id = shipment.id
#                     invoice_modified_at = shipment.modified_at
#                     order_modified_at = order.modified_at
#                     shipment_last_modified_by = shipment.last_modified_by
#                     seller_shop = order.seller_shop
#                     order_id = order.order_no
#                     pin_code = order.shipping_address.pincode
#                     order_status = order.get_order_status_display()
#                     order_date = order.created_at
#                     order_by = order.ordered_by
#                     retailer_id = order.buyer_shop.id
#                     retailer_name = order.buyer_shop
#                     order_invoice = shipment.invoice_no
#                     invoice_date = shipment.created_at
#                     invoice_status = shipment.get_shipment_status_display()
#                     ordered_sku_pieces = products.ordered_qty
#                     shipped_sku_pieces = products.shipped_qty
#                     delivered_sku_pieces = products.delivered_qty
#                     returned_sku_pieces = products.returned_qty
#                     damaged_sku_pieces = products.damaged_qty
#                     sales_person_name = "{} {}".format(order.ordered_by.first_name, order.ordered_by.last_name)
#                     order_type =''
#                     campaign_name =''
#                     discount = ''
#                     OrderDetailReports.objects.using('gfanalytics').create(invoice_id = invoice_id, order_invoice = order_invoice, invoice_date = invoice_date, invoice_modified_at = invoice_modified_at, invoice_last_modified_by = shipment_last_modified_by, invoice_status = invoice_status, order_id = order_id, seller_shop = seller_shop,  order_status = order_status, order_date = order_date, order_modified_at = order_modified_at,  order_by = order_by, retailer_id = retailer_id, retailer_name =retailer_name, pin_code = pin_code, product_id = product_id, product_name = product_name, product_brand = product_brand, product_mrp = product_mrp, product_value_tax_included = product_value_tax_included, ordered_sku_pieces = ordered_sku_pieces,  shipped_sku_pieces = shipped_sku_pieces, delivered_sku_pieces = delivered_sku_pieces, returned_sku_pieces = returned_sku_pieces, damaged_sku_pieces = damaged_sku_pieces, product_cgst = product_cgst, product_sgst = product_sgst, product_igst = product_igst, product_cess = product_cess, sales_person_name = sales_person_name, order_type = order_type, campaign_name = campaign_name, discount = discount)
#                     order_details[i] = {'invoice_id':invoice_id, 'order_invoice':order_invoice, 'invoice_date':invoice_date, 'invoice_modified_at':invoice_modified_at, 'shipment_last_modified_by':shipment_last_modified_by, 'invoice_status':invoice_status, 'order_id':order_id, 'seller_shop':seller_shop,  'order_status':order_status, 'order_date':order_date, 'order_modified_at':order_modified_at, 'order_by':order_by, 'retailer_id':retailer_id, 'retailer_name':retailer_name, 'pin_code':pin_code, 'product_id':product_id, 'product_name':product_name, 'product_brand':product_brand, 'product_mrp':product_mrp, 'product_value_tax_included':product_value_tax_included, 'ordered_sku_pieces':ordered_sku_pieces, 'shipped_sku_pieces':shipped_sku_pieces, 'delivered_sku_pieces':delivered_sku_pieces, 'returned_sku_pieces':returned_sku_pieces, 'damaged_sku_pieces':damaged_sku_pieces, 'product_cgst':product_cgst, 'product_sgst':product_sgst, 'product_igst':product_igst, 'product_cess':product_cess, 'sales_person_name':sales_person_name, 'order_type':order_type, 'campaign_name':campaign_name, 'discount':discount}
#
#         data = order_details
#         return data
#
#     def get(self, *args, **kwargs):
#         from django.http import HttpResponse
#         from django.contrib import messages
#
#         shop_id = self.request.GET.get('shop')
#         start_date = self.request.GET.get('start_date', None)
#         end_date = self.request.GET.get('end_date', None)
#         if end_date and end_date < start_date:
#             messages.error(self.request, 'End date cannot be less than the start date')
#             return render(
#                 self.request,
#                 'admin/services/order-report.html',
#                 {'form': OrderReportForm(user=None, initial=self.request.GET)}
#             )
#         data = self.get_order_report(shop_id, start_date, end_date)
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="order-mis-report.csv"'
#         writer = csv.writer(response)
#         writer.writerow(['S.No.', 'Id', 'Invoice Id', 'Invoice Date', 'Invoice Modified At', 'Invoice Last Modified BY', 'Invoice Status', 'Retailer Contact No.', 'Retailer Id', 'Retailer Name', 'PinCode', 'Order Id', 'Seller Shop', 'Order Status', 'Order Date', 'Order Modified At', 'Sales Person Name', 'Order Type (Organic / Through Sales Person)', 'Campaign Name',  'SKU Id', 'Product Name', 'Product Brand', 'Product MRP' ,'Product Value including tax', 'Ordered SKU Pieces', 'Shipped SKU Pieces', 'Delivered SKU Pieces', 'Returned SKU Pieces', 'Damaged SKU Pieces', 'CGST %', 'SGST %', 'IGST %', 'Cess %',  'Discount %'])
#         for k,v in data.items():
#             writer.writerow([k, v['invoice_id'], v['order_invoice'], v['invoice_date'], v['invoice_modified_at'], v['shipment_last_modified_by'],  v['invoice_status'], v['order_by'], v['retailer_id'], v['retailer_name'], v['pin_code'], v['order_id'], v['seller_shop'], v['order_status'], v['order_date'], v['order_modified_at'], v['sales_person_name'], v['order_type'], v['campaign_name'],   v['product_id'], v['product_name'], v['product_brand'], v['product_mrp'], v['product_value_tax_included'], v['ordered_sku_pieces'], v['shipped_sku_pieces'], v['delivered_sku_pieces'], v['returned_sku_pieces'], v['damaged_sku_pieces'], v['product_cgst'], v['product_sgst'], v['product_igst'], v['product_cess'], v['discount']])
#
#         return response
#
# class OrderReportFormView(View):
#     def get(self, request):
#         form = OrderReportForm(user=request.user)
#         return render(
#             self.request,
#             'admin/services/order-report.html',
#             {'form': form}
#         )
#
#
# class GRNReport(APIView):
#     permission_classes = (AllowAny,)
#
#     def get_grn_report(self, shop_id, start_date, end_date):
#         buyer_shop = Shop.objects.get(pk=shop_id)
#         orders = PurchaseOrder.objects.filter(ordered_cart__gf_shipping_address__shop_name = buyer_shop)
#         if start_date:
#             orders = orders.filter(created_at__gte = start_date)
#         if end_date:
#             orders = orders.filter(created_at__lte = end_date)
#         grn_details = {}
#         i=0
#         for order in orders:
#             for grns in order.order_grn_order.all():
#                 for products in grns.grn_order_grn_order_product.all():
#                     i += 1
#                     try:
#                         product_id = products.product.id
#                         product_name = products.product.product_name
#                         product_brand = products.product.product_brand
#                         product_mrp = products.product.product_vendor_mapping.filter(product = products.product).last().product_mrp
#                         gram_to_brand_price = grns.grn_order_grn_order_product.filter(product = products.product).last().po_product_price
#                         #product_value_tax_included = products.product.product_pro_price.get(status=True, shop = buyer_shop).price_to_retailer
#                         if products.product.product_pro_tax.filter(tax__tax_type ='gst').exists():
#                             product_gst = products.product.product_pro_tax.filter(tax__tax_type ='gst').last()
#                         if order.ordered_cart.supplier_state == order.ordered_cart.gf_shipping_address.state:
#                             product_cgst = (float(product_gst.tax.tax_percentage)/2.0)
#                             product_sgst = (float(product_gst.tax.tax_percentage)/2.0)
#                             product_igst = ''
#                         else:
#                             product_cgst = ''
#                             product_sgst = ''
#                             product_igst = (float(product_gst.tax.tax_percentage))
#                         if products.product.product_pro_tax.filter(tax__tax_type ='cess').exists():
#                             product_cess = products.product.product_pro_tax.filter(tax__tax_type ='cess').last().tax.tax_percentage
#                         else:
#                             product_cess = ''
#                         po_no = order.order_no
#                         po_date = order.created_at
#                         po_status = order.ordered_cart.get_po_status_display()
#                         vendor_name = order.ordered_cart.supplier_name
#                         vendor_id = order.ordered_cart.supplier_name.id
#                         buyer_shop = order.ordered_cart.gf_shipping_address.shop_name
#                         shipping_address = order.ordered_cart.gf_shipping_address.address_line1
#                         category_manager = ''
#                         manufacture_date = grns.grn_order_grn_order_product.get(product = products.product).manufacture_date
#                         expiry_date = grns.grn_order_grn_order_product.get(product = products.product).expiry_date
#                         po_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).po_product_quantity if products.product else ''
#                         discount = ''
#                         grn_id = grns.grn_id
#                         grn_date = grns.created_at
#                         grn_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty if products.product else ''
#                         invoice_item_gross_value = (grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty) * (gram_to_brand_price)
#                         delivered_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).delivered_qty if products.product else ''
#                         returned_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).returned_qty if products.product else ''
#                         dn_number = ''
#                         dn_value_basic =''
#                         GRNReports.objects.using('gfanalytics').create(po_no = po_no, po_date = po_date, po_status = po_status, vendor_name = vendor_name,  vendor_id = vendor_id, buyer_shop=buyer_shop, shipping_address = shipping_address, category_manager = category_manager, product_id = product_id, product_name = product_name, product_brand = product_brand, manufacture_date = manufacture_date, expiry_date = expiry_date, po_sku_pieces = po_sku_pieces, product_mrp = product_mrp, discount = discount,  gram_to_brand_price = gram_to_brand_price, grn_id = grn_id, grn_date = grn_date, grn_sku_pieces = grn_sku_pieces, product_cgst = product_cgst, product_sgst = product_sgst, product_igst = product_igst, product_cess = product_cess, invoice_item_gross_value = invoice_item_gross_value, delivered_sku_pieces = delivered_sku_pieces, returned_sku_pieces = returned_sku_pieces, dn_number = dn_number, dn_value_basic = dn_value_basic)
#                         grn_details[i] = { 'po_no':po_no, 'po_date':po_date, 'po_status':po_status, 'vendor_name':vendor_name, 'vendor_id':vendor_id, 'buyer_shop':buyer_shop, 'shipping_address':shipping_address, 'category_manager':category_manager, 'product_id':product_id, 'product_name':product_name, 'product_brand':product_brand, 'manufacture_date':manufacture_date, 'expiry_date':expiry_date, 'po_sku_pieces':po_sku_pieces, 'product_mrp':product_mrp, 'discount':discount, 'gram_to_brand_price':gram_to_brand_price, 'grn_id':grn_id, 'grn_date':grn_date, 'grn_sku_pieces':grn_sku_pieces, 'product_cgst':product_cgst, 'product_sgst':product_sgst, 'product_igst':product_igst, 'product_cess':product_cess, 'invoice_item_gross_value':invoice_item_gross_value, 'delivered_sku_pieces':delivered_sku_pieces, 'returned_sku_pieces':returned_sku_pieces, 'dn_number':dn_number, 'dn_value_basic':dn_value_basic}
#                     except:
#                         pass
#         data = grn_details
#         return data
#
#     def get(self, *args, **kwargs):
#         from django.http import HttpResponse
#         from django.contrib import messages
#
#         shop_id = self.request.GET.get('shop')
#         start_date = self.request.GET.get('start_date', None)
#         end_date = self.request.GET.get('end_date', None)
#         if end_date and end_date < start_date:
#             messages.error(self.request, 'End date cannot be less than the start date')
#             return render(
#                 self.request,
#                 'admin/services/grn-report.html',
#                 {'form': GRNReportForm(user=None, initial=self.request.GET)}
#             )
#         data = self.get_grn_report(shop_id, start_date, end_date)
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="grn-mis-report.csv"'
#         writer = csv.writer(response)
#         writer.writerow(['S.No.', 'PO No.', 'PO Date', 'PO Status', 'Vendor Name', 'Vendor Id', 'Buyer Shop', 'Shipping Address', 'Category Manager', 'SKU Id', 'Product Name', 'Product Brand', 'Manufacture Date', 'Expiry Date', 'PO SKU Pieces', 'Product MRP', 'Gram to Brand Price', 'Discount %', 'GRN ID', 'GRN Date', 'Invoice SKU Pieces', 'CGST', 'SGST', 'IGST', 'CESS', 'Invoice Item Gross value', 'Delivered SKU Pieces', 'Returned SKU Pieces', 'DN Number', 'DN value (Basic)'])
#         for k,v in data.items():
#             writer.writerow([k, v['po_no'], v['po_date'], v['po_status'], v['vendor_name'], v['vendor_id'], v['buyer_shop'],  v['shipping_address'], v['category_manager'], v['product_id'], v['product_name'], v['product_brand'], v['manufacture_date'], v['expiry_date'], v['po_sku_pieces'], v['product_mrp'], v['gram_to_brand_price'], v['discount'], v['grn_id'], v['grn_date'], v['grn_sku_pieces'], v['product_cgst'], v['product_sgst'], v['product_igst'], v['product_cess'], v['invoice_item_gross_value'], v['delivered_sku_pieces'], v['returned_sku_pieces'], v['dn_number'], v['dn_value_basic']])
#
#         return response
#
# class GRNReportFormView(View):
#     def get(self, request):
#         form = GRNReportForm(user=request.user)
#         return render(
#             self.request,
#             'admin/services/grn-report.html',
#             {'form': form}
#         )
#
#
# class MasterReport(APIView):
#     permission_classes = (AllowAny,)
#
#     def get_master_report(self, shop_id):
#         shop = Shop.objects.get(pk=shop_id)
#         product_prices = ProductPrice.objects.filter(seller_shop=shop, approval_status=ProductPrice.APPROVED)
#         products_list = {}
#         i=0
#         for products in product_prices:
#             i+=1
#             product = products.product
#             mrp = products.mrp
#             price_to_retailer = products.price_to_retailer
#             #New Code for pricing
#             selling_price = products.selling_price if products.selling_price else ''
#             buyer_shop = products.buyer_shop if products.buyer_shop else ''
#             city = products.city if products.city else ''
#             pincode = products.pincode if products.pincode else ''
#
#             product_gf_code = products.product.product_gf_code
#             product_ean_code = products.product.product_ean_code
#             product_brand = products.product.product_brand if products.product.product_brand.brand_parent == None else products.product.product_brand.brand_parent
#             product_subbrand = products.product.product_brand.brand_name if products.product.product_brand.brand_parent != None else ''
#             product_category = products.product.product_pro_category.last().category
#             tax_gst_percentage = 0
#             tax_cess_percentage = 0
#             tax_surcharge_percentage = 0
#             for tax in products.product.product_pro_tax.all():
#                 if tax.tax.tax_type == 'gst':
#                     tax_gst_percentage = tax.tax.tax_percentage
#                 elif tax.tax.tax_type == 'cess':
#                     tax_cess_percentage = tax.tax.tax_percentage
#                 elif tax.tax.tax_type == 'surcharge':
#                     tax_surcharge_percentage = tax.tax.tax_percentage
#             service_partner = products.seller_shop
#             pack_size = products.product.product_inner_case_size
#             case_size = products.product.product_case_size
#             hsn_code = products.product.product_hsn
#             product_id = products.product.id
#             sku_code = products.product.product_sku
#             short_description = products.product.product_short_description
#             long_description = products.product.product_long_description
#             created_at = products.product.created_at
#             MasterReports.objects.using('gfanalytics').create(product = product, service_partner = service_partner,
#             mrp = mrp, price_to_retailer = price_to_retailer, selling_price=selling_price, buyer_shop=buyer_shop, city=city,
#             pincode=pincode, product_gf_code = product_gf_code,  product_brand = product_brand,
#             product_subbrand = product_subbrand, product_category = product_category, tax_gst_percentage = tax_gst_percentage,
#             tax_cess_percentage = tax_cess_percentage, tax_surcharge_percentage = tax_surcharge_percentage, pack_size = pack_size,
#             case_size = case_size, hsn_code = hsn_code, product_id = product_id, sku_code = sku_code,
#             short_description = short_description, long_description = long_description, created_at = created_at)
#
#             products_list[i] = {'product':product, 'service_partner':service_partner, 'mrp':mrp, 'price_to_retailer':price_to_retailer,
#             'selling_price':selling_price, 'buyer_shop':buyer_shop, 'city':city,'pincode':pincode,
#             'product_gf_code':product_gf_code, 'product_brand':product_brand, 'product_subbrand':product_subbrand,
#             'product_category':product_category, 'tax_gst_percentage':tax_gst_percentage, 'tax_cess_percentage':tax_cess_percentage,
#             'tax_surcharge_percentage':tax_surcharge_percentage, 'pack_size':pack_size, 'case_size':case_size, 'hsn_code':hsn_code,
#             'product_id':product_id, 'sku_code':sku_code, 'short_description':short_description, 'long_description':long_description}
#         data = products_list
#         return data
#
#     def get(self, *args, **kwargs):
#         from django.http import HttpResponse
#         from django.contrib import messages
#
#         shop_id = self.request.GET.get('shop')
#         data = self.get_master_report(shop_id)
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="master-report.csv"'
#         writer = csv.writer(response)
#         writer.writerow(['S.No', 'Product Name', 'Service Partner', 'MRP', 'PTR','Selling Price', 'Buyer Shop','City','Pincode', 'GF Code', 'Brand', 'Subbrand', 'Category', 'GST %', 'CESS %', 'Surcharge %', 'Pack Size', 'Case Size', 'HSN', 'Product ID', 'SKU Code', 'Short Desc.', 'Long Desc.'])
#         for k,v in data.items():
#             writer.writerow([k, v['product'], v['service_partner'], v['mrp'], v['price_to_retailer'],
#             v['selling_price'], v['buyer_shop'], v['city'], v['pincode'],
#             v['product_gf_code'], v['product_brand'], v['product_subbrand'], v['product_category'], v['tax_gst_percentage'],
#             v['tax_cess_percentage'], v['tax_surcharge_percentage'], v['pack_size'], v['case_size'], v['hsn_code'],
#             v['product_id'], v['sku_code'], v['short_description'], v['long_description']])
#
#         return response
#
# class MasterReportFormView(View):
#     def get(self, request):
#         form = MasterReportForm(user=request.user)
#         return render(
#             self.request,
#             'admin/services/master-report.html',
#             {'form': form}
#         )
#
# class RetailerProfileReport(APIView):
#     permission_classes = (AllowAny,)
#     def get_unmapped_shops(self):
#         retailers = ParentRetailerMapping.objects.filter(parent__isnull=True)
#         for retailer in retailers:
#             retailer_id = retailer.retailer.id
#             retailer_name = retailer.retailer
#             retailer_type = retailer.retailer.shop_type.shop_type
#             retailer_phone_number = retailer.retailer.shop_owner.phone_number
#             created_at = retailer.retailer.created_at
#             RetailerReports.objects.using('gfanalytics').create(retailer_id = retailer_id, retailer_name = retailer_name, retailer_type=retailer_type, retailer_phone_number=retailer_phone_number, created_at=created_at)
#
#     def get_retailer_report(self, shop_id):
#         shop = Shop.objects.get(pk=shop_id)
#         last_entry = RetailerReports.objects.using('gfanalytics').latest('created_at').created_at
#         retailers = ParentRetailerMapping.objects.filter(parent = shop,created_at__gte=last_entry)
#         retailers_list = {}
#         i=0
#         for retailer in retailers:
#             i+=1
#             retailer_id = retailer.retailer.id
#             retailer_name = retailer.retailer
#             retailer_type = retailer.retailer.shop_type.shop_type
#             retailer_phone_number = retailer.retailer.shop_owner.phone_number
#             created_at = retailer.retailer.created_at
#             #for address in m.retailer.shop_name_address_mapping.all():
#              #   retailer_location = address.address_line1
#               #  retailer_pincode = address.pincode
#             service_partner = shop.shop_name
#             service_partner_id = shop.id or ''
#             service_partner_contact = shop.shop_owner.phone_number if shop else ''
#             sales_manager = ''
#             sales_manager_contact = ''
#             bda_name = ''
#             bda_number = ''
#             RetailerReports.objects.using('gfanalytics').create(retailer_id = retailer_id, retailer_name = retailer_name, retailer_type=retailer_type, retailer_phone_number=retailer_phone_number, created_at=created_at, service_partner=service_partner, service_partner_id=service_partner_id, service_partner_contact=service_partner_contact)
#         data = retailers_list
#         return data
#
#     def get(self, *args, **kwargs):
#         from django.http import HttpResponse
#         from django.contrib import messages
#
#         shop_id = self.request.GET.get('shop')
#         data = self.get_master_report(shop_id)
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="master-report.csv"'
#         writer = csv.writer(response)
#
#         writer.writerow(['S.No', 'Product Name', 'Service Partner', 'MRP', 'PTR', 'Selling Price', 'Buyer Shop', 'City', 'Pincode', 'GF Code', 'Brand', 'Subbrand', 'Category', 'GST %', 'CESS %', 'Surcharge %', 'Pack Size', 'Case Size', 'HSN', 'Product ID', 'SKU Code', 'Short Desc.', 'Long Desc.'])
#         for k,v in data.items():
#             writer.writerow([k, v['product'], v['service_partner'], v['mrp'], v['price_to_retailer'],
#             v['selling_price'], v['buyer_shop'], v['city'], v['pincode'], v['product_gf_code'], v['product_brand'],
#             v['product_subbrand'], v['product_category'], v['tax_gst_percentage'], v['tax_cess_percentage'],
#             v['tax_surcharge_percentage'], v['pack_size'], v['case_size'], v['hsn_code'],  v['product_id'],
#             v['sku_code'], v['short_description'], v['long_description']])
#
#         return response
#
# class RetailerReportFormView(View):
#     def get(self, request):
#         form = RetailerReportFormView(user=request.user)
#         return render(
#             self.request,
#             'admin/services/master-report.html',
#             {'form': form}
#         )
#
# class OrderGrnReport(APIView):
#     permission_classes = (AllowAny,)
#
#     def get_order_grn_report(self, shop_id, start_date, end_date):
#         seller_shop = Shop.objects.get(pk=shop_id)
#         orders = Order.objects.filter(seller_shop = seller_shop)
#         if start_date:
#             orders = orders.filter(created_at__gte = start_date)
#         if end_date:
#             orders = orders.filter(created_at__lte = end_date)
#         order_grn = {}
#         i=0
#         diff = datetime.timedelta(seconds = 20)
#         for order in orders:
#             for grn in order.ordered_cart.sp_ordered_retailer_cart.all():
#                 #print(grn.order_product_reserved)
#                 #print(grn.order_product_reserved.ordered_product)
#                 #print(grn.order_product_reserved.ordered_product.order)
#
#                 i+=1
#                 order_id = order.order_no
#                 if grn.order_product_reserved.ordered_product and grn.order_product_reserved.ordered_product.order:
#                     date = grn.order_product_reserved.ordered_product.order.created_at
#                     date1 = date - diff
#                     grn_gram = GRNOrder.objects.get(created_at__lte = date, created_at__gte=date1)
#                     OrderGrnReports.objects.using('gfanalytics').create(order = order_id, grn = grn_gram)
#                     order_grn[i] = {'order_id':order_id, 'grn_gram':grn_gram}
#         data = order_grn
#         return data
#
#     def get(self, *args, **kwargs):
#         from django.http import HttpResponse
#         from django.contrib import messages
#
#         shop_id = self.request.GET.get('shop')
#         start_date = self.request.GET.get('start_date', None)
#         end_date = self.request.GET.get('end_date', None)
#         if end_date and end_date < start_date:
#             messages.error(self.request, 'End date cannot be less than the start date')
#             return render(
#                 self.request,
#                 'admin/services/order-grn-report.html',
#                 {'form': OrderGrnForm(user=None, initial=self.request.GET)}
#             )
#         data = self.get_order_grn_report(shop_id, start_date, end_date)
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="order-grn-report.csv"'
#         writer = csv.writer(response)
#         writer.writerow(['S.No', 'Order', 'GRN'])
#         for k,v in data.items():
#             writer.writerow([k, v['order_id'], v['grn_gram']])
#
#         return response
#
# class OrderGrnReportFormView(View):
#     def get(self, request):
#         form = OrderGrnForm(user=request.user)
#         return render(
#             self.request,
#             'admin/services/order-grn-report.html',
#             {'form': form}
#         )
#
# class CategoryProductReport(APIView):
#     permission_classes = (AllowAny,)
#
#     def get_category_product_report(self, created_at):
#         products = Product.objects.all()
#         if created_at:
#             products = Product.objects.filter(created_at__gte = created_at)
#         i=0
#         cat_prod_list = {}
#         for product in products:
#             for cat in product.product_pro_category.all():
#                 i+=1
#                 product_id = product.id
#                 product_name = product.product_name
#                 product_short_description = product.product_short_description
#                 product_created_at = product.created_at
#                 category_id = cat.category.id
#                 category = cat.category
#                 category_name = cat.category.category_name
#
#                 CategoryProductReports.objects.using('gfanalytics').create(product_id = product_id, product_name = product_name, product_short_description=product_short_description, product_created_at=product_created_at, category_id=category_id, category=category, category_name=category_name)
#                 cat_prod_list[i] = {'product_id':product_id, 'product_name':product_name, 'product_short_description':product_short_description, 'product_created_at':product_created_at, 'category_id':category_id, 'category':category, 'category_name':category_name}
#         data = cat_prod_list
#         return data
#
#     def get(self, *args, **kwargs):
#         from django.http import HttpResponse
#         from django.contrib import messages
#
#         created_at = self.request.GET.get('created_at', None)
#         data = self.get_category_product_report(created_at)
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="cat-prod-report.csv"'
#         writer = csv.writer(response)
#         writer.writerow(['S.No',  'Product Id', 'Product Name', 'Product Short Description', 'Category ID', 'Category', 'Category Name'])
#         for k,v in data.items():
#             writer.writerow([k,v['product_id'], v['product_name'], v['product_short_description'], v['category_id'], v['category'], v['category_name']])
#
#         return response
#
# class CategoryProductReportFormView(View):
#     def get(self, request):
#         form = CategoryProductReportFormView(user=request.user)
#         return render(
#             self.request,
#             'admin/services/cate-prod-report.html',
#             {'form': form}
#         )
#
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

# class OrderReportData(APIView):
#     permission_classes = (AllowAny,)
#     def get_order_report(self, shop_id, start_date, end_date):
#         seller_shop = Shop.objects.get(pk=shop_id)
# #        last_modified_entry = OrderDetailReportsData.objects.filter(seller_shop=seller_shop_map[str(shop_id)]).latest('order_modified_at'#)
#        # first_modified_entry = OrderDetailReportsData.objects.filter(seller_shop=seller_shop_map[str(shop_id)]).order_by('order_modified_at').first()
#         orders = Order.objects.filter(seller_shop = seller_shop)
#         if start_date:
#             orders = orders.filter(modified_at__gte = start_date)
#         if end_date:
#             orders = orders.filter(modified_at__lte = end_date)
#         order_details = {}
#         i=0
#         for order in orders:
#             for shipment in order.rt_order_order_product.all():
#                 for products in shipment.rt_order_product_order_product_mapping.all():
#                     i += 1
#                     product_id = products.product.id
#                     product_name = products.product.product_name
#                     product_brand = products.product.product_brand
#                     #product_mrp = products.product.product_pro_price.get(status=True, shop = seller_shop).mrp
#                     # product_value_tax_included = products.product.product_pro_price.get(status=True, shop = seller_shop).price_to_retailer
#                     # New Price Logic
#                     # try:
#                     #    product_mrp = products.product.getMRP(seller_shop.id,order.buyer_shop.id)
#                     #    product_value_tax_included = products.product.getRetailerPrice(seller_shop.id,order.buyer_shop.id)
#                     # except:
#                     product_mrp = products.product.product_pro_price.filter(status=True,
#                                                                             seller_shop=seller_shop).last().mrp
#                     product_value_tax_included = products.product.product_pro_price.filter(status=True,
#                                                                                            seller_shop=seller_shop).last().price_to_retailer
#                     for price in order.ordered_cart.rt_cart_list.all():
#                         selling_price = price.cart_product_price.selling_price
#                         item_effective_price = price.item_effective_prices
#
#                     if products.product.product_pro_tax.filter(tax__tax_type='gst').exists():
#                         product_gst = products.product.product_pro_tax.filter(tax__tax_type='gst').last()
#                     if order.shipping_address.state == order.seller_shop.shop_name_address_mapping.filter(
#                             address_type='shipping').last().state:
#                         product_cgst = (float(product_gst.tax.tax_percentage) / 2.0)
#                         product_sgst = (float(product_gst.tax.tax_percentage) / 2.0)
#                         product_igst = ''
#                     else:
#                         product_cgst = ''
#                         product_sgst = ''
#                         product_igst = (float(product_gst.tax.tax_percentage))
#                     if products.product.product_pro_tax.filter(tax__tax_type='cess').exists():
#                         product_cess = products.product.product_pro_tax.filter(
#                             tax__tax_type='cess').last().tax.tax_percentage
#                     else:
#                         product_cess = ''
#                     invoice_id = shipment.id
#                     invoice_modified_at = shipment.modified_at
#                     order_modified_at = order.modified_at
#                     shipment_last_modified_by = shipment.last_modified_by
#                     seller_shop = order.seller_shop
#                     order_id = order.order_no
#                     pin_code = order.shipping_address.pincode
#                     order_status = order.get_order_status_display()
#                     order_date = order.created_at
#                     order_by = order.ordered_by
#                     retailer_id = order.buyer_shop.id
#                     retailer_name = order.buyer_shop
#                     order_invoice = shipment.invoice_no
#                     invoice_date = shipment.created_at
#                     invoice_status = shipment.get_shipment_status_display()
#                     ordered_sku_pieces = products.ordered_qty
#                     shipped_sku_pieces = products.shipped_qty
#                     delivered_sku_pieces = products.delivered_qty
#                     returned_sku_pieces = products.returned_qty
#                     damaged_sku_pieces = products.damaged_qty
#                     sales_person_name = "{} {}".format(order.ordered_by.first_name, order.ordered_by.last_name)
#                     order_type = ''
#                     campaign_name = ''
#                     discount = ''
#                     trip = ''
#                     trip_id = ''
#                     trip_status = ''
#                     delivery_boy = ''
#                     trip_created_at = None
#                     if shipment and shipment.trip:
#                         trip = shipment.trip.dispatch_no
#                         trip_id = shipment.trip.id
#                         trip_id = shipment.trip.id
#                         trip_status = shipment.trip.trip_status
#                         delivery_boy = shipment.trip.delivery_boy
#                         trip_created_at = shipment.trip.created_at
#                     OrderDetailReportsData.objects.using('gfanalytics').create(invoice_id=invoice_id,
#                                                                                order_invoice=order_invoice,
#                                                                                invoice_date=invoice_date,
#                                                                                invoice_modified_at=invoice_modified_at,
#                                                                                invoice_last_modified_by=shipment_last_modified_by,
#                                                                                invoice_status=invoice_status,
#                                                                                order_id=order_id,
#                                                                                seller_shop=seller_shop,
#                                                                                order_status=order_status,
#                                                                                order_date=order_date,
#                                                                                order_modified_at=order_modified_at,
#                                                                                order_by=order_by,
#                                                                                retailer_id=retailer_id,
#                                                                                retailer_name=retailer_name,
#                                                                                pin_code=pin_code, product_id=product_id,
#                                                                                product_name=product_name,
#                                                                                product_brand=product_brand,
#                                                                                product_mrp=product_mrp,
#                                                                                product_value_tax_included=product_value_tax_included,
#                                                                                ordered_sku_pieces=ordered_sku_pieces,
#                                                                                shipped_sku_pieces=shipped_sku_pieces,
#                                                                                delivered_sku_pieces=delivered_sku_pieces,
#                                                                                returned_sku_pieces=returned_sku_pieces,
#                                                                                damaged_sku_pieces=damaged_sku_pieces,
#                                                                                product_cgst=product_cgst,
#                                                                                product_sgst=product_sgst,
#                                                                                product_igst=product_igst,
#                                                                                product_cess=product_cess,
#                                                                                sales_person_name=sales_person_name,
#                                                                                order_type=order_type,
#                                                                                campaign_name=campaign_name,
#                                                                                discount=discount, trip=trip,
#                                                                                trip_id=trip_id, trip_status=trip_status,
#                                                                                delivery_boy=delivery_boy,
#                                                                                trip_created_at=trip_created_at,
#                                                                                selling_price=selling_price,
#                                                                                item_effective_price=item_effective_price)
#                     order_details[i] = {'invoice_id': invoice_id, 'order_invoice': order_invoice,
#                                         'invoice_date': invoice_date, 'invoice_modified_at':invoice_modified_at, 'shipment_last_modified_by':shipment_last_modified_by, 'invoice_status':invoice_status, 'order_id':order_id, 'seller_shop':seller_shop,  'order_status':order_status, 'order_date':order_date, 'order_modified_at':order_modified_at, 'order_by':order_by, 'retailer_id':retailer_id, 'retailer_name':retailer_name, 'pin_code':pin_code, 'product_id':product_id, 'product_name':product_name, 'product_brand':product_brand, 'product_mrp':product_mrp, 'product_value_tax_included':product_value_tax_included, 'ordered_sku_pieces':ordered_sku_pieces, 'shipped_sku_pieces':shipped_sku_pieces, 'delivered_sku_pieces':delivered_sku_pieces, 'returned_sku_pieces':returned_sku_pieces, 'damaged_sku_pieces':damaged_sku_pieces, 'product_cgst':product_cgst, 'product_sgst':product_sgst, 'product_igst':product_igst, 'product_cess':product_cess, 'sales_person_name':sales_person_name, 'order_type':order_type, 'campaign_name':campaign_name, 'discount':discount,
#                                         'trip':trip,'trip_id':trip_id, 'trip_status':trip_status,'delivery_boy':delivery_boy,'trip_created_at':trip_created_at, 'selling_price':selling_price, 'item_effective_price':item_effective_price}
#                     data = order_details
#                     return data
#
# class CartProductMappingReport(APIView):
#     permission_classes=(AllowAny,)
#
#     def cart_product_mapping_report(self, id):
#         cpm  = CartProductMapping.objects.filter(id=id)
#         # last_modified_entry = TripShipmentReport.objects.filter(seller_shop=seller_shop_map[str(id)]).latest('order_modified_at')
#         # first_modified_entry = TripShipmentReport.objects.filter(seller_shop=seller_shop_map[str(id)]).order_by('order_modified_at').first()
#         # start_date = first_modified_entry
#         # end_date=last_modified_entry
#         # shipment = OrderedProduct.objects.filter(id=id)
#         # if start_date:
#         #     shipment = OrderedProduct.orders.filter(modified_at__gte=start_date)
#         # if end_date:
#         #     shipment = OrderedProduct.orders.filter(modified_at__lte=end_date)
#         cartproductmapping_details = {}
#         i=0
#         for values in cpm:
#             i+=1
#             cart= values.cart.order_id
#             qty = values.qty
#             qty_error_msg= values.qty_error_msg
#             created_at = values.created_at
#             modified_at = values.modified_at
#             cart_product = values.cart_product.product_name
#             cart_product_price = values.cart_product_price.selling_price
#             no_of_pieces = values.no_of_pieces
#             status = values.status
#             CartProductMappingData.objects.using('gfanalytics').create(cart=cart, qty=qty, qty_error_msg=qty_error_msg,
#                                                                        created_at=created_at, modified_at=modified_at,
#                                                                        cart_product=cart_product,
#                                                                        cart_product_price=cart_product_price,
#                                                                        no_of_pieces=no_of_pieces, status=status)
#             cartproductmapping_details[i] = {'cart': cart, 'qty': qty, 'qty_error_msg': qty_error_msg,
#                                              'created_at': created_at, 'modified_at': modified_at,
#                                              'cart_product': cart_product, 'cart_product_price': cart_product_price,
#                                              'no_of_pieces': no_of_pieces, 'status': status}
#
#         data = cartproductmapping_details
#         return data
#
#
# def OrderReportType(request):
#     response =  requests.get('http://127.0.0.1:8000/services/api/v1/orderReport-type/2/')
#     data = response.json()
#     return render(request, 'admin/services/orderReport.html',{
#         "id":data['id'],
#         "invoice_id":data['invoice_id'],
#         "order_invoice":data['order_invoice'],
#         "invoice_date":data["invoice_date"],
#         "invoice_modified_at":data["invoice_modified_at"],
#         "invoice_last_modified_by":data["invoice_last_modified_by"]
#
#
#     })

class InOutLedgerReport(APIView):
    permission_classes = (AllowAny,)

    def get_in_out_ledger_report(self, product_id, warehouse_id, start_date, end_date, inventory_types_qs):
        sku_id = Product.objects.filter(id=product_id).last().product_sku
        ins = In.objects.filter(sku=sku_id, warehouse=warehouse_id, created_at__gte=start_date,
                                created_at__lte=end_date)
        outs = Out.objects.filter(sku=sku_id, warehouse=warehouse_id, created_at__gte=start_date,
                                  created_at__lte=end_date)
        data = sorted(chain(ins, outs), key=lambda instance: instance.created_at)

        ins_type_wise_qty = ins.values('inventory_type').order_by('inventory_type').annotate(total_qty=Sum('quantity'))
        out_type_wise_qty = outs.values('inventory_type').order_by('inventory_type').annotate(total_qty=Sum('quantity'))

        in_type_ids = {x['inventory_type']: x['total_qty'] for x in ins_type_wise_qty}
        out_type_ids = {x['inventory_type']: x['total_qty'] for x in out_type_wise_qty}

        ins_count_list = ['TOTAL IN QUANTITY']
        outs_count_list = ['TOTAL OUT QUANTITY']
        for i in range(len(inventory_types_qs)):
            if i + 1 in in_type_ids:
                ins_count_list.append(in_type_ids[i + 1])
            else:
                ins_count_list.append('0')
            if i + 1 in out_type_ids:
                outs_count_list.append(out_type_ids[i + 1])
            else:
                outs_count_list.append('0')
        return data, ins_count_list, outs_count_list

    def get(self, *args, **kwargs):
        from django.http import HttpResponse
        from django.contrib import messages
        sku_id = self.request.GET.get('sku')
        warehouse_id = self.request.GET.get('warehouse')
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        if end_date and end_date < start_date:
            messages.error(self.request, 'End date cannot be less than the start date')
            return render(
                self.request,
                'admin/services/in-out-ledger.html',
                {'form': InOutLedgerForm(initial=self.request.GET)}
            )
        it_qs = InventoryType.objects.values('id', 'inventory_type').order_by('id')
        inventory_types = list(x['inventory_type'].upper() for x in it_qs)
        data, ins_qtylst, outs_qtylst = self.get_in_out_ledger_report(sku_id, warehouse_id, start_date, end_date, it_qs)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ledger-report.csv"'
        writer = csv.writer(response)
        writer.writerow([''] + inventory_types)
        writer.writerow(ins_qtylst)
        writer.writerow(outs_qtylst)
        writer.writerow([])
        writer.writerow(['TIMESTAMP', 'SKU', 'WAREHOUSE', 'INVENTORY TYPE', 'IN TYPE', 'OUT TYPE', 'TRANSACTION ID',
                         'QUANTITY'])
        for obj in data:
            if obj.__class__.__name__ == 'In':
                writer.writerow([obj.created_at, obj.sku, obj.warehouse, obj.inventory_type, obj.in_type, None,
                                 obj.in_type_id, obj.quantity])
            elif obj.__class__.__name__ == 'Out':
                writer.writerow([obj.created_at, obj.sku, obj.warehouse, obj.inventory_type, None, obj.out_type,
                                 obj.out_type_id, obj.quantity])
            else:
                writer.writerow([obj.created_at, obj.sku, obj.warehouse, obj.inventory_type, None, None, None,
                                 obj.quantity])
        return response


class InOutLedgerFormView(View):
    def get(self, request):
        form = InOutLedgerForm()
        return render(
            self.request,
            'admin/services/in-out-ledger.html',
            {'form': form}
        )