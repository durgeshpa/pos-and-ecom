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
from shops.models import Shop
from django.db.models import Sum
import json
import csv
from rest_framework import permissions, authentication
from .forms import SalesReportForm
from django.views import View
from products.models import Product, ProductPrice, ProductOption,ProductImage, ProductTaxMapping
# Create your views here.
class SalesReport(APIView):
    permission_classes = (AllowAny,)

    def get_sales_report(self, shop_id, start_date, end_date):
        seller_shop = Shop.objects.get(pk=shop_id)
        orders = Order.objects.using('readonly').filter(seller_shop = seller_shop).all()
        if start_date:
            orders = orders.filter(created_at__gte = start_date)
        if end_date:
            orders = orders.filter(created_at__lte = end_date)
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
                tax_sum = 0
                if all_tax_list.exists():
                    for tax in all_tax_list.using('readonly').all():
                        tax_sum = float(tax_sum) + float(tax.tax.tax_percentage)
                    tax_sum = round(tax_sum, 2)
                    get_tax_val = tax_sum / 100
                product_price_to_retailer = cart_product_mapping.cart_product_price.price_to_retailer
                ordered_amount = round((float(product_price_to_retailer)*int(ordered_qty)) / (float(get_tax_val) + 1), 2)
                ordered_tax_amount = round((float(ordered_amount) * float(get_tax_val)), 2)
                if product_shipments:
                    delivered_amount = round((float(product_price_to_retailer)*int(product_shipments)) / (float(get_tax_val) + 1), 2)
                else:
                    delivered_amount = 0
                delivered_tax_amount = round((float(delivered_amount) * float(get_tax_val)), 2)
                if product.product_gf_code in ordered_items:
                    ordered_items[product.product_gf_code]['ordered_qty'] += ordered_qty
                    ordered_items[product.product_gf_code]['ordered_amount'] += ordered_amount
                    ordered_items[product.product_gf_code]['ordered_tax_amount'] += ordered_tax_amount
                    if product_shipments:
                        ordered_items[product.product_gf_code]['delivered_qty'] += product_shipments
                    ordered_items[product.product_gf_code]['delivered_amount'] += delivered_amount
                    ordered_items[product.product_gf_code]['delivered_tax_amount'] += delivered_tax_amount
                else:
                    ordered_items[product.product_gf_code] = {'product_sku':product_sku, 'product_id':product_id, 'product_name':product_name,'product_brand':product_brand,'ordered_qty':ordered_qty, 'delivered_qty':0, 'ordered_amount':ordered_amount, 'ordered_tax_amount':ordered_tax_amount, 'delivered_amount':delivered_amount, 'delivered_tax_amount':delivered_tax_amount}

        data = ordered_items
        return data

    def get(self, *args, **kwargs):
        shop_id = self.request.GET.get('shop')
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
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
        form = SalesReportForm()
        return render(
            self.request,
            'admin/services/sales-report.html',
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
