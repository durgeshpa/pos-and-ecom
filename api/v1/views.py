from django.shortcuts import render
import datetime
import json
from celery.task import task
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import permissions, authentication
from products.models import Product, ProductPrice
from services.models import RetailerReports, OrderReports,GRNReports, MasterReports, OrderGrnReports, OrderDetailReports, CategoryProductReports
from .serializers import ProductSerializer, ProductPriceSerializer, OrderSerializer, PurchaseOrderSerializer, ShopSerializer, ParentRetailerSerializer
from rest_framework.response import Response
from rest_framework import status
from shops.models import Shop, ParentRetailerMapping
from gram_to_brand.models import Order as PurchaseOrder
from retailer_to_sp.models import Order

class CategoryProductReport(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ProductSerializer
    authentication_classes = (authentication.TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            print(serializer)
            if serializer.is_valid():
                print(request.data)
                #print(Product.objects.filter(product_name__icontains='dfgdgdfg')[0].id)
                product = Product.objects.get(id=request.data.get("id"))
                for cat in product.product_pro_category.all():
                    product_id = product.id
                    product_name = product.product_name
                    product_short_description = product.product_short_description
                    product_created_at = product.created_at
                    category_id = cat.category.id
                    category = cat.category
                    category_name = cat.category.category_name
                    CategoryProductReports.objects.using('dataanalytics').create(product_id = product_id,
                    product_name = product_name, product_short_description=product_short_description, product_created_at=product_created_at,
                    category_id=category_id, category=category, category_name=category_name)
                return Response({"message": [""], "response_data": '', "is_success": True})
            else:
                errors = []
                for field in serializer.errors:
                    for error in serializer.errors[field]:
                        if 'non_field_errors' in field:
                            result = error
                        else:
                            result = ''.join('{} : {}'.format(field,error))
                        errors.append(result)
                msg = {'is_success': False,
                        'message': [error for error in errors],
                        'response_data': None }
                return Response(msg,status=status.HTTP_406_NOT_ACCEPTABLE)
        except Exception as e:
            msg = {'is_success': False,
                   'message': [str(e)],
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

class GRNReport(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ShopSerializer
    authentication_class = (authentication.TokenAuthentication, )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # buyer_shop = Shop.objects.get(pk=request.data.get("id"))
        orders = PurchaseOrder.objects.filter(id=request.data["order_id"])
        grn_details = {}
        i=0
        for order in orders:
            for grns in order.order_grn_order.all():
                for products in grns.grn_order_grn_order_product.all():
                    i += 1
                    product_id = products.product.id
                    product_name = products.product.product_name
                    product_brand = products.product.product_brand
                    product_mrp = products.product.product_vendor_mapping.filter(product = products.product).last().product_mrp
                    gram_to_brand_price = grns.grn_order_grn_order_product.filter(product = products.product).last().po_product_price
                    #product_value_tax_included = products.product.product_pro_price.get(status=True, shop = buyer_shop).price_to_retailer
                    if products.product.product_pro_tax.filter(tax__tax_type ='gst').exists():
                        product_gst = products.product.product_pro_tax.filter(tax__tax_type ='gst').last()
                    if order.ordered_cart.supplier_state == order.ordered_cart.gf_shipping_address.state:
                        product_cgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_sgst = (float(product_gst.tax.tax_percentage)/2.0)
                        product_igst = ''
                    else:
                        product_cgst = ''
                        product_sgst = ''
                        product_igst = (float(product_gst.tax.tax_percentage))
                    if products.product.product_pro_tax.filter(tax__tax_type ='cess').exists():
                        product_cess = products.product.product_pro_tax.filter(tax__tax_type ='cess').last().tax.tax_percentage
                    else:
                        product_cess = ''
                    po_no = order.order_no
                    po_date = order.created_at
                    po_status = order.ordered_cart.get_po_status_display()
                    vendor_name = order.ordered_cart.supplier_name
                    vendor_id = order.ordered_cart.supplier_name.id
                    buyer_shop = order.ordered_cart.gf_shipping_address.shop_name
                    shipping_address = order.ordered_cart.gf_shipping_address.address_line1
                    category_manager = ''
                    manufacture_date = grns.grn_order_grn_order_product.get(product = products.product).manufacture_date
                    expiry_date = grns.grn_order_grn_order_product.get(product = products.product).expiry_date
                    po_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).po_product_quantity if products.product else ''
                    discount = ''
                    grn_id = grns.grn_id
                    grn_date = grns.created_at
                    grn_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty if products.product else ''
                    invoice_item_gross_value = (grns.grn_order_grn_order_product.get(product = products.product).product_invoice_qty) * (gram_to_brand_price)
                    delivered_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).delivered_qty if products.product else ''
                    returned_sku_pieces = grns.grn_order_grn_order_product.get(product = products.product).returned_qty if products.product else ''
                    dn_number = ''
                    dn_value_basic =''
                    GRNReports.objects.using('dataanalytics').create(po_no = po_no, po_date = po_date, po_status = po_status, vendor_name = vendor_name,  vendor_id = vendor_id, buyer_shop=buyer_shop, shipping_address = shipping_address, category_manager = category_manager, product_id = product_id, product_name = product_name, product_brand = product_brand, manufacture_date = manufacture_date, expiry_date = expiry_date, po_sku_pieces = po_sku_pieces, product_mrp = product_mrp, discount = discount,  gram_to_brand_price = gram_to_brand_price, grn_id = grn_id, grn_date = grn_date, grn_sku_pieces = grn_sku_pieces, product_cgst = product_cgst, product_sgst = product_sgst, product_igst = product_igst, product_cess = product_cess, invoice_item_gross_value = invoice_item_gross_value, delivered_sku_pieces = delivered_sku_pieces, returned_sku_pieces = returned_sku_pieces, dn_number = dn_number, dn_value_basic = dn_value_basic)
                    grn_details[i] = { 'po_no':po_no, 'po_date':po_date, 'po_status':po_status, 'vendor_name':vendor_name, 'vendor_id':vendor_id, 'buyer_shop':buyer_shop, 'shipping_address':shipping_address, 'category_manager':category_manager, 'product_id':product_id, 'product_name':product_name, 'product_brand':product_brand, 'manufacture_date':manufacture_date, 'expiry_date':expiry_date, 'po_sku_pieces':po_sku_pieces, 'product_mrp':product_mrp, 'discount':discount, 'gram_to_brand_price':gram_to_brand_price, 'grn_id':grn_id, 'grn_date':grn_date, 'grn_sku_pieces':grn_sku_pieces, 'product_cgst':product_cgst, 'product_sgst':product_sgst, 'product_igst':product_igst, 'product_cess':product_cess, 'invoice_item_gross_value':invoice_item_gross_value, 'delivered_sku_pieces':delivered_sku_pieces, 'returned_sku_pieces':returned_sku_pieces, 'dn_number':dn_number, 'dn_value_basic':dn_value_basic}

                data = grn_details
            return Response({"message": [""], "response_data": '', "is_success": True})

class MasterReport(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ProductPriceSerializer
    authentication_classes = (authentication.TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            shop = Shop.objects.get(pk=request.data["seller_shop_id"])
            product_prices = ProductPrice.objects.filter(seller_shop=shop, approval_status=ProductPrice.APPROVED)
            products_list = {}
            i=0
            for products in product_prices:
                i+=1
                product = products.product
                mrp = products.mrp
                price_to_retailer = products.price_to_retailer
                #New Code for pricing
                selling_price = products.selling_price if products.selling_price else ''
                buyer_shop = products.buyer_shop if products.buyer_shop else ''
                city = products.city if products.city else ''
                pincode = products.pincode if products.pincode else ''

                product_gf_code = products.product.product_gf_code
                product_ean_code = products.product.product_ean_code
                product_brand = products.product.product_brand if products.product.product_brand.brand_parent == None else products.product.product_brand.brand_parent
                product_subbrand = products.product.product_brand.brand_name if products.product.product_brand.brand_parent != None else ''
                product_category = products.product.product_pro_category.last().category
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
                service_partner = products.seller_shop
                pack_size = products.product.product_inner_case_size
                # case_size = products.product.product_case_size
                hsn_code = products.product.product_hsn
                product_id = products.product.id
                sku_code = products.product.product_sku
                short_description = products.product.product_short_description
                long_description = products.product.product_long_description
                created_at = products.product.created_at
                MasterReports.objects.using('dataanalytics').create(product = product, service_partner = service_partner,
                mrp = mrp, price_to_retailer = price_to_retailer, selling_price=selling_price, buyer_shop=buyer_shop, city=city,
                pincode=pincode, product_gf_code = product_gf_code,  product_brand = product_brand,
                product_subbrand = product_subbrand, product_category = product_category, tax_gst_percentage = tax_gst_percentage,
                tax_cess_percentage = tax_cess_percentage, tax_surcharge_percentage = tax_surcharge_percentage, pack_size = pack_size,
                case_size = case_size, hsn_code = hsn_code, product_id = product_id, sku_code = sku_code,
                short_description = short_description, long_description = long_description, created_at = created_at)

                products_list[i] = {'product':product, 'service_partner':service_partner, 'mrp':mrp, 'price_to_retailer':price_to_retailer,
                'selling_price':selling_price, 'buyer_shop':buyer_shop, 'city':city,'pincode':pincode,
                'product_gf_code':product_gf_code, 'product_brand':product_brand, 'product_subbrand':product_subbrand,
                'product_category':product_category, 'tax_gst_percentage':tax_gst_percentage, 'tax_cess_percentage':tax_cess_percentage,
                'tax_surcharge_percentage':tax_surcharge_percentage, 'pack_size':pack_size, 'case_size':case_size, 'hsn_code':hsn_code,
                'product_id':product_id, 'sku_code':sku_code, 'short_description':short_description, 'long_description':long_description}
            data = products_list
        return Response({"message": [""], "response_data": '', "is_success": True})


class OrderReport(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = OrderSerializer
    authentication_classes = (authentication.TokenAuthentication,)

    def create(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                order_details = {}
                order = Order.objects.filter(id=request.data['order_id']).last()
                seller_shop=order.seller_shop
                for shipment in order.rt_order_order_product.all():
                    for products in shipment.rt_order_product_order_product_mapping.all():
                        product_id = products.product.id
                        product_name = products.product.product_name
                        product_brand = products.product.product_brand
                        # product_mrp = products.product.product_pro_price.filter(status=True, seller_shop = seller_shop)
                        # for i in product_mrp:
                        #     mrp = i.mrp
                        # product_value_tax_included = products.product.product_pro_price.filter(status=True, seller_shop = seller_shop)
                        # for i in product_value_tax_included:
                        #     price_to_retailer=i.price _to_retailer
                        product_mrp = products.product.product_pro_price.filter(status=True,
                                                                                seller_shop=seller_shop).last().mrp
                        product_value_tax_included = products.product.product_pro_price.filter(status=True,
                                                                                               seller_shop=seller_shop).last().price_to_retailer
                        # product_mrp = products.product.getMRP(order.seller_shop.id, order.buyer_shop.id)
                        # product_value_tax_included = products.product.getRetailerPrice(order.seller_shop.id,order.buyer_shop.id)

                        if products.product.product_pro_tax.filter(tax__tax_type ='gst').exists():
                            product_gst = products.product.product_pro_tax.filter(tax__tax_type ='gst').last()
                        if order.shipping_address.state == order.seller_shop.shop_name_address_mapping.filter(address_type='shipping').last().state:
                            product_cgst = (float(product_gst.tax.tax_percentage)/2.0)
                            product_sgst = (float(product_gst.tax.tax_percentage)/2.0)
                            product_igst = ''
                        else:
                            product_cgst = ''
                            product_sgst = ''
                            product_igst = (float(product_gst.tax.tax_percentage))
                        if products.product.product_pro_tax.filter(tax__tax_type ='cess').exists():
                            product_cess = products.product.product_pro_tax.filter(tax__tax_type ='cess').last().tax.tax_percentage
                        else:
                            product_cess = ''
                        invoice_id = shipment.id
                        invoice_modified_at = shipment.modified_at
                        order_modified_at = order.modified_at
                        shipment_last_modified_by = shipment.last_modified_by
                        seller_shop = order.seller_shop
                        order_id = order.order_no
                        pin_code = order.shipping_address.pincode
                        order_status = order.get_order_status_display()
                        order_date = order.created_at
                        order_by = order.ordered_by
                        retailer_id = order.buyer_shop.id
                        retailer_name = order.buyer_shop
                        order_invoice = shipment.invoice_no
                        invoice_date = shipment.created_at
                        invoice_status = shipment.get_shipment_status_display()
                        ordered_sku_pieces = products.ordered_qty
                        shipped_sku_pieces = products.shipped_qty
                        delivered_sku_pieces = products.delivered_qty
                        returned_sku_pieces = products.returned_qty
                        damaged_sku_pieces = products.damaged_qty
                        sales_person_name=''
                        if order.ordered_by:
                            sales_person_name = "{} {}".format(order.ordered_by.first_name, order.ordered_by.last_name)
                        order_type =''
                        campaign_name =''
                        discount = ''
                        OrderDetailReports.objects.using('dataanalytics').create(invoice_id = invoice_id, order_invoice = order_invoice,
                        invoice_date = invoice_date, invoice_modified_at = invoice_modified_at, invoice_last_modified_by = shipment_last_modified_by,
                        invoice_status = invoice_status, order_id = order_id, seller_shop = seller_shop,  order_status = order_status,
                        order_date = order_date, order_modified_at = order_modified_at,  order_by = order_by, retailer_id = retailer_id,
                        retailer_name =retailer_name, pin_code = pin_code, product_id = product_id, product_name = product_name,
                        product_brand = product_brand,product_mrp=product_mrp, product_value_tax_included=product_value_tax_included, ordered_sku_pieces = ordered_sku_pieces,  shipped_sku_pieces = shipped_sku_pieces, delivered_sku_pieces = delivered_sku_pieces,
                        returned_sku_pieces = returned_sku_pieces, damaged_sku_pieces = damaged_sku_pieces, product_cgst = product_cgst,
                        product_sgst = product_sgst, product_igst = product_igst, product_cess = product_cess, sales_person_name = sales_person_name,
                        order_type = order_type, campaign_name = campaign_name, discount = discount)
                return Response({"message": [""], "response_data": '', "is_success": True})



class RetailerProfileReport(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ParentRetailerSerializer
    authentication_class = (authentication.TokenAuthentication,)


    # def get_unmapped_shops(self):
    #     retailers = ParentRetailerMapping.objects.filter(parent__isnull=True)
    #     for retailer in retailers:
    #         retailer_id = retailer.retailer.id
    #         retailer_name = retailer.retailer
    #         retailer_type = retailer.retailer.shop_type.shop_type
    #         retailer_phone_number = retailer.retailer.shop_owner.phone_number
    #         created_at = retailer.retailer.created_at
    #         RetailerReports.objects.using('gfanalytics').create(retailer_id=retailer_id, retailer_name=retailer_name,
    #                                                             retailer_type=retailer_type,
    #                                                             retailer_phone_number=retailer_phone_number,
    #                                                             created_at=created_at)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.data)
        # shop = Shop.objects.get(pk=request.data.get("shop_id"))
        retailers = ParentRetailerMapping.objects.filter(retailer_id=request.data["retailer_id"], status=True)
        retailers_list = {}
        i = 0
        for retailer in retailers:
            i += 1
            retailer_id = retailer.retailer.id
            retailer_name = retailer.retailer
            retailer_type = retailer.retailer.shop_type.shop_type
            retailer_phone_number = retailer.retailer.shop_owner.phone_number
            created_at = retailer.retailer.created_at
            service_partner = retailer.parent.shop_name
            service_partner_id = retailer.parent.id or ''
            service_partner_contact = retailer.parent.shop_owner.phone_number if retailer.parent else ''
            RetailerReports.objects.using('dataanalytics').create(retailer_id=retailer_id, retailer_name=retailer_name,
                                                                retailer_type=retailer_type,
                                                                retailer_phone_number=retailer_phone_number,
                                                                created_at=created_at, service_partner=service_partner,
                                                                service_partner_id=service_partner_id,
                                                                service_partner_contact=service_partner_contact)
        data = retailers_list
        return Response({"message": [""], "response_data": '', "is_success": True})




