from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist

from sp_to_gram.tasks import es_search
from .serializers import ProductDetailSerializer
from products.models import Product
from shops.models import Shop

class ProductDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    """
        API to get information of existing gramfactory product for POS product creation
    """
    def get(self, *args, **kwargs):
        pk = self.kwargs.get('pk')
        msg = {'is_success': False, 'message':'', 'response_data': None}
        try:
            product = Product.objects.get(id=pk)
        except ObjectDoesNotExist:
            msg['message'] = 'Invalid Product ID'
            return Response(msg, status=status.HTTP_200_OK)

        product_detail_serializer = ProductDetailSerializer(product)
        return Response({"message": 'Success', "response_data": product_detail_serializer.data, "is_success": True})


class RetailerProductsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def search_query(self, keyword):
        filter_list = []
        if keyword:
            filter_list = [{"match": {"name": {"query": keyword, "fuzziness": "AUTO", "operator": "or",
                                               "minimum_should_match": "2"}}}]
        return {"bool": {"filter": filter_list}}

    def process_results(self, products_list):
        p_list = []
        for p in products_list['hits']['hits']:
            mrp = p["_source"]["mrp"]
            sp = p["_source"]["selling_price"]
            p["_source"]["margin"] = ((mrp - sp) / mrp) * 100
            p_list.append(p["_source"])
        return p_list

    def get_response(self, data, msg):
        if data:
            ret = {"message": msg, "response_data": data, "is_success": True}
        else:
            ret = {"message": msg, "response_data": None, "is_success": False}
        return Response(ret, status=200)

    def get(self, request, *args, **kwargs):
        """
        API to search for retailer products of a particular shop
        Inputs:
        shop_id
        keyword (search for product name)
        """
        search_keyword = request.GET.get('keyword')
        shop_id = request.GET.get('shop_id')
        if not Shop.objects.filter(id=shop_id, status=True).exists():
            return self.get_response([], 'Shop Not Found/Active')
        query = self.search_query(search_keyword)
        body = { "from": 0, "size": 5, "query": query, "_source": {"includes": ["name", "selling_price", "mrp",
                                                                                "images"]}}
        products_list = es_search(index="rp-{}".format(shop_id), body=body)
        p_list = self.process_results(products_list)
        return self.get_response(p_list, 'products for shop')