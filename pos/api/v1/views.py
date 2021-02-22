from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist

from sp_to_gram.tasks import es_search
from .serializers import ProductDetailSerializer
from products.models import Product, Brand
from shops.models import Shop
from categories import models as categorymodel


class ProductDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    """
        API to get information of existing GramFactory product for POS product creation
    """

    def get(self, *args, **kwargs):
        pk = self.kwargs.get('pk')
        msg = {'is_success': False, 'message': '', 'response_data': None}
        try:
            product = Product.objects.get(id=pk)
        except ObjectDoesNotExist:
            msg['message'] = 'Invalid Product ID'
            return Response(msg, status=status.HTTP_200_OK)

        product_detail_serializer = ProductDetailSerializer(product)
        return Response(
            {"message": 'Product Found', "response_data": product_detail_serializer.data, "is_success": True})


class RetailerProductsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def search_query(self, request):
        filter_list = []
        query = {"bool": {"filter": filter_list}}

        brands = request.GET.get('brands')
        categories = request.GET.get('categories')
        keyword = request.GET.get('product_name')

        if not (categories or brands or keyword):
            return query

        if brands:
            brand_name = "{} -> {}".format(Brand.objects.filter(id__in=list(brands)).last(), keyword)
            filter_list.append({"match": {"brand": {"query": brand_name, "fuzziness": "AUTO", "operator": "and"}}})
        elif keyword:
            q = {"multi_match": {"query": keyword, "fields": ["name^5", "category", "brand"], "type": "cross_fields"}}
            query["bool"]["must"] = [q]
        if categories:
            category_filter = str(categorymodel.Category.objects.filter(id__in=categories, status=True).last())
            filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})

        return query

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

    def get(self, request):
        """
        API to search for retailer products of a particular shop
        Inputs:
        shop_id
        keyword (search for product name)
        """
        shop_id = request.GET.get('shop_id')
        if not Shop.objects.filter(id=shop_id, status=True).exists():
            return self.get_response([], 'Shop Not Found/Active')
        query = self.search_query(request)
        body = {"from": 0, "size": 5, "query": query, "_source": {"includes": ["name", "selling_price", "mrp",
                                                                               "images"]}}
        products_list = es_search(index="rp-{}".format(shop_id), body=body)
        p_list = self.process_results(products_list)
        return self.get_response(p_list, 'Products Found For Shop' if p_list else 'No Products Found')


class EanSearch(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        ean_code = request.GET.get('ean_code')
        if ean_code and ean_code != '':
            body = {
                "from": int(request.GET.get('offset', 0)),
                "size": int(request.GET.get('pro_count', 50)),
                "query": {"bool": {"filter": [{"term": {"status": True}}, {"match": {"ean": {"query": ean_code}}}]}},
                "_source": {
                    "includes": ["id", "name", "product_images"]}
            }
            products_list = es_search(index="all_products", body=body)
            p_list = self.process_results(products_list)
            return self.get_response(p_list, 'Products Found' if p_list else 'No Products Found')
        else:
            return self.get_response([], 'Provide Ean Code')

    def process_results(self, products_list):
        p_list = []
        for p in products_list['hits']['hits']:
            p_list.append(p["_source"])
        return p_list

    def get_response(self, data, msg):
        if data:
            ret = {"message": msg, "response_data": data, "is_success": True}
        else:
            ret = {"message": msg, "response_data": None, "is_success": False}
        return Response(ret, status=200)


class GramProductsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        query = self.search_query(request)
        body = {
            "from": int(request.GET.get('offset', 0)),
            "size": int(request.GET.get('pro_count', 50)),
            "query": query,
            "_source": {
                "includes": ["id", "name", "product_images"]}
        }
        products_list = es_search(index="all_products", body=body)
        p_list = self.process_results(products_list)
        return self.get_response(p_list, 'Products Found' if p_list else 'No Products Found')

    def search_query(self, request):
        filter_list = [
            {"term": {"status": True}},
        ]
        query = {"bool": {"filter": filter_list}}

        product_ids = request.GET.get('product_ids')
        if product_ids:
            filter_list.append({"ids": {"type": "product", "values": product_ids}})
            return query

        brands = request.GET.get('brands')
        categories = request.GET.get('categories')
        keyword = request.GET.get('product_name')

        if not (categories or brands or keyword):
            return query

        if brands:
            brand_name = "{} -> {}".format(Brand.objects.filter(id__in=list(brands)).last(), keyword)
            filter_list.append({"match": {"brand": {"query": brand_name, "fuzziness": "AUTO", "operator": "and"}}})
        elif keyword:
            q = {"multi_match": {"query": keyword, "fields": ["name^5", "category", "brand"], "type": "cross_fields"}}
            query["bool"]["must"] = [q]
        if categories:
            category_filter = str(categorymodel.Category.objects.filter(id__in=categories, status=True).last())
            filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})

        return query

    def process_results(self, products_list):
        p_list = []
        for p in products_list['hits']['hits']:
            p_list.append(p["_source"])
        return p_list

    def get_response(self, data, msg):
        if data:
            ret = {"message": msg, "response_data": data, "is_success": True}
        else:
            ret = {"message": msg, "response_data": None, "is_success": False}
        return Response(ret, status=200)
