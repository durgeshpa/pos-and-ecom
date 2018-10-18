from rest_framework import generics
from .serializers import ProductsSearchSerializer,GramGRNProductsSearchSerializer
from products.models import Product, ProductPrice, ProductOption
from gram_to_brand.models import GRNOrderProductMapping
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

class ProductsList(generics.ListCreateAPIView):
    permission_classes = (AllowAny,)
    model = Product
    serializer_class = ProductsSearchSerializer

    def get_queryset(self):
        grn = GRNOrderProductMapping.objects.all()
        p_list = []
        for p in grn:
            product = p.product
            id = product.pk
            p_list.append(id)

        products = Product.objects.filter(pk__in=p_list)
        for product in products:
            name = product.product_name
            product_price = ProductPrice.objects.get(product=product)
            mrp = product_price.mrp
            ptr = product_price.price_to_retailer
            status = product_price.status
            product_option = ProductOption.objects.get(product=product)
            pack_size = product_option.package_size.pack_size_name
            weight = product_option.weight.weight_name
            return name, mrp, ptr, status, pack_size, weight

class GramGRNProductsList(APIView):
    permission_classes = (AllowAny,)
    serializer_class = GramGRNProductsSearchSerializer

    def post(self, request, format=None):
        grn = GRNOrderProductMapping.objects.all()
        p_id_list = []
        for p in grn:
            product = p.product
            id = product.pk
            p_id_list.append(id)
        products = Product.objects.filter(pk__in=p_id_list)
        p_list = []
        for product in products:
            id = product.pk
            name = product.product_name
            product_price = ProductPrice.objects.get(product=product)
            mrp = product_price.mrp
            ptr = product_price.price_to_retailer
            status = product_price.status
            product_option = ProductOption.objects.get(product=product)
            pack_size = product_option.package_size.pack_size_name
            weight = product_option.weight.weight_name
            if name.startswith(request.data['product_name']):
                p_list.append({"name":name, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "weight":weight})
        if not p_list:
            msg = {'is_success': False,
                    'message': ['Sorry no product found!'],
                    'response_data': None }
            return Response(msg,
                            status=400)

        msg = {'is_success': True,
                'message': ['Products found'],
                'response_data':p_list }
        return Response(msg,
                        status=200)
