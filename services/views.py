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
# Create your views here.
class SalesReport(ListAPIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):

        shop_id = self.request.GET.get('shop_id')
        seller_shop = Shop.objects.get(pk=shop_id)
        orders = Order.objects.filter(seller_shop = seller_shop).all()
        ordered_items = {}
        for order in orders:
            for cart_product_mapping in order.ordered_cart.rt_cart_list.all():
                product = cart_product_mapping.cart_product
                product_name = cart_product_mapping.cart_product.product_name
                ordered_qty = cart_product_mapping.no_of_pieces
                product_shipments = OrderedProductMapping.objects.filter(
                    product=product,
                    ordered_product__order__seller_shop = seller_shop
                    ).aggregate(
                    Sum('delivered_qty'))['delivered_qty__sum']
                if product.product_gf_code in ordered_items:
                    ordered_items[product.product_gf_code]['ordered_qty'] += ordered_qty
                else:
                    ordered_items[product.product_gf_code] = {'product_name':product_name,'ordered_qty':ordered_qty, 'delivered_qty':product_shipments}
        data = ordered_items
        return HttpResponse( json.dumps( data ) )



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
