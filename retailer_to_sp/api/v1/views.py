import logging
import json
from datetime import datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F,Sum, Q
from wkhtmltopdf.views import PDFTemplateResponse
from django.shortcuts import get_object_or_404, get_list_or_404
from django.utils import timezone
from django.contrib.postgres.search import SearchVector
from django_filters import rest_framework as filters
from rest_framework import permissions, authentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import serializers
from rest_framework import generics, viewsets

from .serializers import (ProductsSearchSerializer,GramGRNProductsSearchSerializer,
    CartProductMappingSerializer,CartSerializer, OrderSerializer,
    CustomerCareSerializer, OrderNumberSerializer, PaymentCodSerializer,
    PaymentNeftSerializer,GramPaymentCodSerializer,GramPaymentNeftSerializer,
    GramMappedCartSerializer,GramMappedOrderSerializer,ProductDetailSerializer,
    OrderDetailSerializer, OrderedProductSerializer, OrderedProductMappingSerializer,
    RetailerShopSerializer, SellerOrderListSerializer,OrderListSerializer,
    ReadOrderedProductSerializer,FeedBackSerializer, CancelOrderSerializer,
    ShipmentDetailSerializer, TripSerializer, ShipmentSerializer
)

from products.models import Product, ProductPrice, ProductOption,ProductImage, ProductTaxMapping
from sp_to_gram.models import (OrderedProductMapping,OrderedProductReserved, OrderedProductMapping as SpMappedOrderedProductMapping,
                                OrderedProduct as SPOrderedProduct, StockAdjustment)

from categories import models as categorymodel

from gram_to_brand.models import (GRNOrderProductMapping, CartProductMapping as GramCartProductMapping,
    OrderedProductReserved as GramOrderedProductReserved, PickList, PickListItems
)
from retailer_to_sp.models import (Cart, CartProductMapping, Order,
    OrderedProduct, Payment, CustomerCare, Return, Feedback, OrderedProductMapping as ShipmentProducts, Trip
)


from retailer_to_gram.models import ( Cart as GramMappedCart,CartProductMapping as GramMappedCartProductMapping,
    Order as GramMappedOrder, OrderedProduct as GramOrderedProduct, Payment as GramMappedPayment,
    CustomerCare as GramMappedCustomerCare
)

from shops.models import Shop, ParentRetailerMapping
from shops.models import Shop,ParentRetailerMapping, ShopUserMapping
from brand.models import Brand
from products.models import ProductCategory
from addresses.models import Address
from retailer_backend.common_function import getShopMapping,checkNotShopAndMapping,getShop
from retailer_backend.messages import ERROR_MESSAGES

from retailer_to_sp.tasks import (
    ordered_product_available_qty_update, release_blocking, create_reserved_order
)
from .filters import OrderedProductMappingFilter, OrderedProductFilter

from common.data_wrapper_view import DataWrapperViewSet

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from common.data_wrapper import format_serializer_errors
from sp_to_gram.tasks import es_search


User = get_user_model()

logger = logging.getLogger(__name__)

today = datetime.today()


class OrderedProductViewSet(DataWrapperViewSet):
    '''
    This class handles all operation of ordered product
    '''
    #permission_classes = (AllowAny,)
    model = OrderedProduct
    queryset = OrderedProduct.objects.all()
    serializer_class = OrderedProductSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = OrderedProductFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': ReadOrderedProductSerializer,
            'list':ReadOrderedProductSerializer,
            'create':OrderedProductSerializer,
            'update':OrderedProductSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def get_queryset(self):
        shipment_id = self.request.query_params.get('shipment_id', None)
        ordered_product = OrderedProduct.objects.all()

        if shipment_id is not None:
            ordered_product = ordered_product.filter(
                id=shipment_id
                )
        return ordered_product


class OrderedProductMappingView(DataWrapperViewSet):
    '''
    This class handles all operation of ordered product mapping
    '''
    #permission_classes = (AllowAny,)
    model = ShipmentProducts
    serializer_class = OrderedProductMappingSerializer
    queryset = ShipmentProducts.objects.all()
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = OrderedProductMappingFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': OrderedProductMappingSerializer,
            'list':OrderedProductMappingSerializer,
            'create':OrderedProductMappingSerializer,
            'update':OrderedProductMappingSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def get_queryset(self):
        ordered_product = self.request.query_params.get('ordered_product', None)
        ordered_product_mapping = ShipmentProducts.objects.all()
        if ordered_product is not None:
            ordered_product_mapping = ordered_product_mapping.filter(
                ordered_product=ordered_product
                )
        return ordered_product_mapping



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

    def search_query(self, request):
        filter_list = [{"term":{"status":True}}]
        if self.product_ids:
            filter_list.append( {"ids":{"type":"product", "values":self.product_ids}})
            query = {"bool":{"filter":filter_list}}
            return query
        if self.category or self.brand or self.keyword:
            query = {"bool":{"filter":filter_list}}
        else:
            return {"match_all":{}}
        if not self.brand and self.keyword:
            q = {
            "match":{
                "name":{"query":self.keyword, "fuzziness":"AUTO", "operator":"and"}
                }
            }
        #else:
        #    q = {"match_all":{}}
            filter_list.append(q)
        if self.brand:
            filter_list.append({"match": {"brand":str(Brand.objects.filter(id__in=list(self.brand)).last())}})
        if self.category:
            category_filter = str(categorymodel.Category.objects.filter(id__in=self.category, status=True).last())
            q = {
                "match" :{
                    "category":{"query":category_filter,"operator":"and"}
                }
            }
            filter_list.append(q)
        return query

    def post(self, request, format=None):
        self.product_ids = request.data.get('product_ids')
        self.brand = request.data.get('brands')
        self.category = request.data.get('categories')
        self.keyword = request.data.get('product_name', None)
        shop_id = request.data.get('shop_id')
        offset = int(request.data.get('offset',0))
        page_size = int(request.data.get('pro_count',20))
        grn_dict = None
        cart_check = False
        is_store_active = True
        sort_preference = request.GET.get('sort_by_price')

        '''1st Step
            Check If Shop Is exists then 2nd pt else 3rd Pt
        '''
        query = self.search_query(request)

        try:
            shop = Shop.objects.get(id=shop_id,status=True)
        except ObjectDoesNotExist:
            '''3rd Step
                If no shop found then
            '''
            message = "Shop not active or does not exists"
            is_store_active = False
        else:
            '''2nd Step
                Check if shop fond then check weather it is sp 4th Step or retailer 5th Step
            '''
            try:
                parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
            except ObjectDoesNotExist:
                message = "Shop Mapping Not Found"
                is_store_active = False
            else:

                if parent_mapping.parent.shop_type.shop_type == 'sp':
                    '''4th Step
                        SP mapped data shown
                    '''
                    body = {"from" : offset, "size" : page_size, "query":query}
                    products_list = es_search(index=parent_mapping.parent.id, body=body)
                    cart = Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).last()
                    if cart:
                        cart_products = cart.rt_cart_list.all()
                        cart_check = True
                else:
                    is_store_active = False
        p_list = []
        if not is_store_active:
            body = {
                "from" : offset,
                "size" : page_size,
                "query":query,"_source":{"includes":["name", "product_images","pack_size","weight_unit","weight_value"]}
                }
            products_list = es_search(index="all_products", body=body)

        for p in products_price:
            user_selected_qty = None
            no_of_pieces = None
            sub_total = None
            name = p.product.product_name
            mrp = round(p.mrp, 2) if p.mrp else p.mrp
            ptr = round(p.price_to_retailer, 2) if p.price_to_retailer else p.price_to_retailer
            loyalty_discount = round(p.loyalty_incentive, 2) if p.loyalty_incentive else p.loyalty_incentive
            cash_discount = round(p.cash_discount, 2) if p.cash_discount else p.cash_discount
            margin = round((100 * (float(mrp) - float(ptr) - (float(cash_discount) + float(loyalty_discount)) * float(
                mrp) / 100) / float(mrp)), 2) if mrp and ptr else 0
        for p in products_list['hits']['hits']:

            if cart_check == True:
                ptr = p["_source"]['ptr']
                loyalty_discount = p["_source"]['loyalty_discount']
                cash_discount = p["_source"]['cash_discount']
                for c_p in cart_products:
                    if c_p.cart_product_id == p["_source"]["id"]:
                        user_selected_qty = c_p.qty
                        no_of_pieces = int(c_p.qty) * int(c_p.cart_product.product_inner_case_size)
                        p["_source"]["user_selected_qty"] = user_selected_qty
                        p["_source"]["no_of_pieces"] = no_of_pieces
                        p["_source"]["sub_total"] = float(no_of_pieces) * float(ptr)
            p_list.append(p["_source"])

        msg = {'is_store_active': is_store_active,
                'is_success': True,
                 'message': ['Products found'],
                 'response_data':p_list }
        if not p_list:
            msg = {'is_store_active': is_store_active,
                    'is_success': False,
                     'message': ['Sorry! No product found'],
                     'response_data':None }
        return Response(msg,
                         status=200)


class ProductDetail(APIView):

    def get(self,*args,**kwargs):
        pk= self.kwargs.get('pk')
        msg = {'is_success': False,'message': [''],'response_data': None}
        try:
           product = Product.objects.get(id=pk)
        except ObjectDoesNotExist:
           msg['message'] = ["Invalid Product name or ID"]
           return Response(msg, status=status.HTTP_200_OK)

        product_detail= Product.objects.get(id=pk)
        product_detail_serializer = ProductsSearchSerializer(product_detail)
        return Response({"message":[''], "response_data": product_detail_serializer.data ,"is_success": True})

class AddToCart(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self,request):
        cart_product = self.request.POST.get('cart_product')
        qty = self.request.POST.get('qty')
        shop_id = self.request.POST.get('shop_id')
        msg = {'is_success': False,'message': ['Sorry no any mapping with any shop!'],'response_data': None}

        if Shop.objects.filter(id=shop_id).exists():

            # get Product
            try:
                product = Product.objects.get(id=cart_product)
            except ObjectDoesNotExist:
                msg['message'] = ["Product not Found"]
                return Response(msg, status=status.HTTP_200_OK)

            if checkNotShopAndMapping(shop_id):
                return Response(msg, status=status.HTTP_200_OK)

            parent_mapping = getShopMapping(shop_id)
            if parent_mapping is None:
                return Response(msg, status=status.HTTP_200_OK)

            if qty is None or qty=='':
                msg['message'] = ["Qty not Found"]
                return Response(msg, status=status.HTTP_200_OK)
            #  if shop mapped with SP

            if parent_mapping.parent.shop_type.shop_type == 'sp':
                if Cart.objects.filter(last_modified_by=self.request.user,
                                       cart_status__in=['active', 'pending']).exists():
                    cart = Cart.objects.filter(last_modified_by=self.request.user,
                                               cart_status__in=['active', 'pending']).last()
                    cart.cart_status = 'active'
                    cart.seller_shop = parent_mapping.parent
                    cart.buyer_shop = parent_mapping.retailer
                    cart.save()
                else:
                    cart = Cart(last_modified_by=self.request.user, cart_status='active')
                    cart.seller_shop = parent_mapping.parent
                    cart.buyer_shop = parent_mapping.retailer
                    cart.save()

                if int(qty) == 0:
                    if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                        CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

                else:
                    cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                    cart_mapping.qty = qty
                    cart_mapping.no_of_pieces = int(qty) * int(product.product_inner_case_size)
                    cart_mapping.save()


                if cart.rt_cart_list.count() <= 0:
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],'response_data': None}
                else:
                    serializer = CartSerializer(Cart.objects.get(id=cart.id),context={'parent_mapping_id': parent_mapping.parent.id})
                    msg = {'is_success': True, 'message': ['Data added to cart'], 'response_data': serializer.data}
                return Response(msg, status=status.HTTP_200_OK)

            #  if shop mapped with gf
            elif parent_mapping.parent.shop_type.shop_type == 'gf':
                if GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                 cart_status__in=['active', 'pending']).exists():
                    cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                         cart_status__in=['active', 'pending']).last()
                    cart.cart_status = 'active'
                    cart.save()
                else:
                    cart = GramMappedCart(last_modified_by=self.request.user, cart_status='active')
                    cart.save()

                if int(qty) == 0:
                    if GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                        GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

                else:
                    cart_mapping, _ = GramMappedCartProductMapping.objects.get_or_create(cart=cart,
                                                                                         cart_product=product)
                    cart_mapping.qty = qty
                    cart_mapping.save()

                if cart.rt_cart_list.count() <= 0:
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],'response_data': None}
                else:
                    serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id),context={'parent_mapping_id': parent_mapping.parent.id})

                    msg = {'is_success': True, 'message': ['Data added to cart'], 'response_data': serializer.data}
                return Response(msg, status=status.HTTP_200_OK)

            else:
                msg = {'is_success': False,
                       'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                       'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)


        else:
            return Response(msg,status=status.HTTP_200_OK)

    def sp_mapping_cart(self, qty,product):
        pass

    def gf_mapping_cart(self,qty,product):
        pass
class CartDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def delivery_message(self):
        date_time_now = datetime.now()
        day = date_time_now.strftime("%A")
        time = date_time_now.strftime("%H")

        if int(time) < 17 and not (day == 'Saturday'):
            return str('Order now and get delivery by {}'.format(
                (date_time_now + timedelta(days=1)).strftime('%A')))
        elif (day == 'Friday'):
            return str('Order now and get delivery by {}'.format(
                (date_time_now + timedelta(days=3)).strftime('%A')))
        else:
            return str('Order now and get delivery by {}'.format(
                (date_time_now + timedelta(days=2)).strftime('%A')))

    def get(self, request, *args, **kwargs):
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Sorry shop or shop mapping not found'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with sp
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            if Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).exists():
                cart = Cart.objects.filter(last_modified_by=self.request.user,
                                           cart_status__in=['active', 'pending']).last()
                if cart.rt_cart_list.count() <= 0:
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                           'response_data': None}
                else:
                    serializer = CartSerializer(
                        Cart.objects.get(id=cart.id),
                        context={'parent_mapping_id': parent_mapping.parent.id,
                                 'delivery_message': self.delivery_message()}
                    )
                    msg = {
                        'is_success': True,
                        'message': [''],
                        'response_data': serializer.data
                    }
                return Response(msg, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                       'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with gf
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            if GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                             cart_status__in=['active', 'pending']).exists():
                cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                     cart_status__in=['active', 'pending']).last()
                if cart.rt_cart_list.count()<=0:
                    msg =  {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],'response_data': None}
                else:
                    serializer = GramMappedCartSerializer(
                        GramMappedCart.objects.get(id=cart.id),
                        context={'parent_mapping_id': parent_mapping.parent.id,
                                 'delivery_message': self.delivery_message()}
                    )
                    msg = {'is_success': True, 'message': [
                        ''], 'response_data': serializer.data}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                       'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)

        else:
            msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)


class ReservedOrder(generics.ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        shop_id = self.request.POST.get('shop_id')
        msg = {'is_success': False,
               'message': ['No any product available in this cart'],
               'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if not parent_mapping:
            return Response(msg, status=status.HTTP_200_OK)

        parent_shop_type = parent_mapping.parent.shop_type.shop_type
        # if shop mapped with sp
        if parent_shop_type == 'sp':
            cart = Cart.objects.filter(last_modified_by=self.request.user,
                                       cart_status__in=['active', 'pending'])
            if cart.exists():
                cart = cart.last()
                cart_products = CartProductMapping.objects.select_related(
                    'cart_product'
                ).filter(
                    cart=cart
                )
                # Check if products available in cart
                if cart_products.count() <= 0:
                    msg = {'is_success': False,
                           'message': ['No product is available in cart'],
                           'response_data': None}
                    return Response(msg, status=status.HTTP_200_OK)

                cart_products.update(qty_error_msg='')
                cart_product_ids = cart_products.values('cart_product')
                shop_products_available = OrderedProductMapping.get_shop_stock(parent_mapping.parent).filter(product__in=cart_product_ids,available_qty__gt=0).values('product_id').annotate(available_qty=Sum('available_qty'))
                shop_products_dict = {g['product_id']:int(g['available_qty']) for g in shop_products_available}

                products_available = {}
                products_unavailable = []
                for cart_product in cart_products:
                    product_availability = shop_products_dict.get(cart_product.cart_product.id, 0)

                    ordered_amount = (
                        int(cart_product.qty) *
                        int(cart_product.cart_product.product_inner_case_size))

                    if product_availability >= ordered_amount:
                        products_available[cart_product.cart_product.id] = ordered_amount
                    else:
                        cart_product.qty_error_msg = ERROR_MESSAGES['AVAILABLE_PRODUCT'].format(int(product_availability)) #TODO: Needs to be improved
                        cart_product.save()
                        products_unavailable.append(cart_product.id)

                if products_unavailable:
                    logger.exception("products unavailable")
                    serializer = CartSerializer(
                        cart,
                        context={
                            'parent_mapping_id':parent_mapping.parent.id
                        })
                    msg = {'is_success': True,
                           'message': [''],
                           'response_data': serializer.data}
                    return Response(msg, status=status.HTTP_200_OK)
                else:
                    reserved_args = json.dumps({
                        'shop_id': parent_mapping.parent.id,
                        'cart_id': cart.id,
                        'products': products_available
                        })
                    create_reserved_order(reserved_args)
            serializer = CartSerializer(cart, context={
                'parent_mapping_id': parent_mapping.parent.id})
            msg = {
                    'is_success': True,
                    'message': [''],
                    'response_data': serializer.data
                }
            return Response(msg, status=status.HTTP_200_OK)
        else:
            msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)
        return Response(msg, status=status.HTTP_200_OK)

    # def sp_mapping_order_reserve(self):
    #     pass
    # def gf_mapping_order_reserve(self):
    #     pass

class CreateOrder(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request,*args, **kwargs):
        cart_id = self.request.POST.get('cart_id')
        billing_address_id = self.request.POST.get('billing_address_id')
        shipping_address_id = self.request.POST.get('shipping_address_id')

        total_tax_amount = self.request.POST.get('total_tax_amount',0)

        shop_id = self.request.POST.get('shop_id')
        msg = {'is_success': False, 'message': ['Have some error in shop or mapping'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        shop = getShop(shop_id)
        if shop is None:
            return Response(msg, status=status.HTTP_200_OK)

        # get billing address
        try:
            billing_address = Address.objects.get(id=billing_address_id)
        except ObjectDoesNotExist:
            msg['message'] = ['Billing address not found']
            return Response(msg, status=status.HTTP_200_OK)

        # get shipping address
        try:
            shipping_address = Address.objects.get(id=shipping_address_id)
        except ObjectDoesNotExist:
            msg['message'] = ['Shipping address not found']
            return Response(msg, status=status.HTTP_200_OK)

        current_url = request.get_host()
        # if shop mapped with sp
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            #self.sp_mapping_order_reserve()
            if Cart.objects.filter(last_modified_by=self.request.user, id=cart_id).exists():
                cart = Cart.objects.get(last_modified_by=self.request.user, id=cart_id)
                cart.cart_status = 'ordered'
                cart.buyer_shop = shop
                cart.seller_shop = parent_mapping.parent
                cart.save()

                if OrderedProductReserved.objects.filter(cart=cart).exists():
                    order,_ = Order.objects.get_or_create(last_modified_by=request.user,ordered_by=request.user, ordered_cart=cart, order_no=cart.order_id)

                    order.billing_address = billing_address
                    order.shipping_address = shipping_address
                    order.buyer_shop = shop
                    order.seller_shop = parent_mapping.parent
                    order.total_tax_amount = float(total_tax_amount)
                    order.order_status = order.ORDERED
                    order.save()

                    # Changes OrderedProductReserved Status
                    for ordered_reserve in OrderedProductReserved.objects.filter(cart=cart, reserve_status=OrderedProductReserved.RESERVED):
                        ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
                        ordered_reserve.order_product_reserved.save()
                        ordered_reserve.reserve_status = OrderedProductReserved.ORDERED
                        ordered_reserve.save()

                    serializer = OrderSerializer(order,context={'parent_mapping_id': parent_mapping.parent.id,'current_url':current_url})
                    msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                else:
                    msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                    return Response(msg, status=status.HTTP_200_OK)

            return Response(msg, status=status.HTTP_200_OK)


        # if shop mapped with gf
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            if GramMappedCart.objects.filter(last_modified_by=self.request.user, id=cart_id).exists():
                cart = GramMappedCart.objects.get(last_modified_by=self.request.user,id=cart_id)
                cart.cart_status = 'ordered'
                cart.save()

                if GramOrderedProductReserved.objects.filter(cart=cart).exists():
                    order,_ = GramMappedOrder.objects.get_or_create(last_modified_by=request.user,ordered_by=request.user, ordered_cart=cart, order_no=cart.order_id)

                    order.billing_address = billing_address
                    order.shipping_address = shipping_address
                    order.buyer_shop = shop
                    order.seller_shop = parent_mapping.parent
                    order.order_status = 'ordered'
                    order.save()

                    pick_list = PickList.objects.get(cart=cart)
                    pick_list.order = order
                    pick_list.status = True
                    pick_list.save()

                    # Remove Data From OrderedProductReserved
                    for ordered_reserve in GramOrderedProductReserved.objects.filter(cart=cart):
                        ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
                        ordered_reserve.order_product_reserved.save()
                        ordered_reserve.reserve_status = 'ordered'
                        ordered_reserve.save()

                    serializer = GramMappedOrderSerializer(order,context={'parent_mapping_id': parent_mapping.parent.id,'current_url':current_url})
                    msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                else:
                    msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                    return Response(msg, status=status.HTTP_200_OK)

        else:
            msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                       'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)
        return Response(msg, status=status.HTTP_200_OK)


#OrderedProductMapping.objects.filter()

class OrderList(generics.ListAPIView):
    serializer_class = OrderListSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        user = self.request.user
        #queryset = self.get_queryset()
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        current_url = request.get_host()
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            queryset = Order.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
            serializer = OrderListSerializer(queryset, many=True, context={'parent_mapping_id': parent_mapping.parent.id,'current_url':current_url})
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            queryset = GramMappedOrder.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
            serializer = GramMappedOrderSerializer(queryset, many=True, context={'parent_mapping_id': parent_mapping.parent.id,'current_url':current_url})

        if serializer.data:
            msg = {'is_success': True,'message': None,'response_data': serializer.data}
        return Response(msg,status=status.HTTP_200_OK)

class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def retrieve(self, request, *args,**kwargs):
        pk = self.kwargs.get('pk')
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        current_url = request.get_host()
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            queryset = Order.objects.get(id=pk)
            serializer = OrderDetailSerializer(queryset, context={'parent_mapping_id': parent_mapping.parent.id,'current_url':current_url})
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            queryset = GramMappedOrder.objects.get(id=pk)
            serializer = GramMappedOrderSerializer(queryset,context={'parent_mapping_id': parent_mapping.parent.id,'current_url':current_url})

        if serializer.data:
            msg = {'is_success': True,'message': None,'response_data': serializer.data}
        return Response(msg,status=status.HTTP_200_OK)

class DownloadInvoiceSP(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'invoice.pdf'
    template_name = 'admin/invoice/invoice_sp.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))

        #order_obj1= get_object_or_404(OrderedProductMapping)
        pk=self.kwargs.get('pk')
        a = OrderedProduct.objects.get(pk=pk)
        shop=a
        payment_type=''
        products = a.rt_order_product_order_product_mapping.filter(shipped_qty__gt=0)
        if a.order.rt_payment.filter(order_id=a.order).exists():
            payment_type = a.order.rt_payment.last().payment_choice
        order_id= a.order.order_no
        shop_id = shop.order.buyer_shop.id

        sum_qty = 0
        sum_amount=0
        tax_inline=0
        total_tax_sum = 0
        taxes_list = []
        gst_tax_list= []
        cess_tax_list= []
        surcharge_tax_list=[]
        for z in shop.order.seller_shop.shop_name_address_mapping.all():
            shop_name_gram= z.shop_name
            nick_name_gram= z.nick_name
            address_line1_gram= z.address_line1
            city_gram= z.city
            state_gram= z.state
            pincode_gram= z.pincode
            address_contact_number= z.address_contact_number

        seller_shop_gistin = '---'
        buyer_shop_gistin = '---'

        if order_obj.order.ordered_cart.seller_shop.shop_name_documents.exists():
            seller_shop_gistin = order_obj.order.ordered_cart.seller_shop.shop_name_documents.filter(
            shop_document_type='gstin').last().shop_document_number if order_obj.order.ordered_cart.seller_shop.shop_name_documents.filter(shop_document_type='gstin').exists() else '---'

        if order_obj.order.ordered_cart.buyer_shop.shop_name_documents.exists():
            buyer_shop_gistin = order_obj.order.ordered_cart.buyer_shop.shop_name_documents.filter(
            shop_document_type='gstin').last().shop_document_number if order_obj.order.ordered_cart.buyer_shop.shop_name_documents.filter(shop_document_type='gstin').exists() else '---'

        product_listing = []
        for m in products:

            # New Code For Product Listing Start
            tax_sum = 0
            basic_rate = 0
            product_tax_amount = 0
            product_pro_price_mrp =0
            product_pro_price_ptr = 0

            no_of_pieces = 0
            cart_qty = 0
            product_tax_amount = 0
            basic_rate = 0
            inline_sum_amount = 0

            cart_product_map = order_obj.order.ordered_cart.rt_cart_list.filter(cart_product=m.product).last()
            product_price = cart_product_map.get_cart_product_price(order_obj.order.ordered_cart.seller_shop)

            product_pro_price_ptr = product_price.price_to_retailer
            product_pro_price_mrp = round(product_price.mrp,2)

            no_of_pieces = m.product.rt_cart_product_mapping.last().no_of_pieces
            cart_qty = m.product.rt_cart_product_mapping.last().qty

            # new code for tax start
            tax_sum = m.get_product_tax_json()

            get_tax_val = tax_sum / 100
            basic_rate = (float(product_pro_price_ptr)) / (float(get_tax_val) + 1)
            base_price = (float(product_pro_price_ptr) * float(m.shipped_qty)) / (float(get_tax_val) + 1)
            product_tax_amount = float(base_price) * float(get_tax_val)

            ordered_prodcut = {
                "product_sku": m.product.product_gf_code,
                "product_short_description": m.product.product_short_description,
                "product_hsn": m.product.product_hsn,
                "product_tax_percentage": "" if tax_sum == 0 else str(tax_sum) + "%",
                "product_mrp": product_pro_price_mrp,
                "shipped_qty": m.shipped_qty,
                "product_inner_case_size": m.product.product_inner_case_size,
                "product_no_of_pices": int(m.shipped_qty),
                "basic_rate": basic_rate,
                "basic_amount": float(m.shipped_qty) * float(basic_rate),
                "price_to_retailer": product_pro_price_ptr,
                "product_sub_total": float(m.shipped_qty) * float(product_pro_price_ptr),
                "product_tax_amount": round(product_tax_amount, 2),

            }
            total_tax_sum = total_tax_sum + product_tax_amount
            inline_sum_amount = inline_sum_amount + product_pro_price_ptr
            product_listing.append(ordered_prodcut)
            # New Code For Product Listing End

            sum_qty += int(m.shipped_qty)
            sum_amount += int(m.shipped_qty) * product_pro_price_ptr
            inline_sum_amount += int(m.shipped_qty) * product_pro_price_ptr

            for n in m.product.product_pro_tax.all():
                divisor= (1+(n.tax.tax_percentage/100))
                original_amount= (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type=='gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type=='cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type=='surcharge':
                    surcharge_tax_list.append(tax_amount)

                taxes_list.append(tax_amount)
                igst= sum(gst_tax_list)
                cgst= (sum(gst_tax_list))/2
                sgst= (sum(gst_tax_list))/2
                cess= sum(cess_tax_list)
                surcharge= sum(surcharge_tax_list)
                #tax_inline = tax_inline + (inline_sum_amount - original_amount)
                #tax_inline1 =(tax_inline / 2)

        total_amount = sum_amount
        total_amount_int = int(total_amount)

        data = {"object": order_obj,"order": order_obj.order,"products":products ,"shop":shop,"shop_id":shop_id, "sum_qty": sum_qty,
                "sum_amount":sum_amount,"url":request.get_host(), "scheme": request.is_secure() and "https" or "http" ,
                "igst":igst, "cgst":cgst,"sgst":sgst,"cess":cess,"surcharge":surcharge, "total_amount":total_amount,
                "order_id":order_id,"shop_name_gram":shop_name_gram,"nick_name_gram":nick_name_gram, "city_gram":city_gram,
                "address_line1_gram":address_line1_gram, "pincode_gram":pincode_gram,"state_gram":state_gram,
                "payment_type":payment_type,"total_amount_int":total_amount_int,"product_listing":product_listing,
                "seller_shop_gistin":seller_shop_gistin,"buyer_shop_gistin":buyer_shop_gistin,
                "address_contact_number":address_contact_number,"sum_amount_tax":round(total_tax_sum, 2)}

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response



class DownloadNote(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'note.pdf'
    template_name = 'admin/invoice/note.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))
        data = {"object": order_obj, }
        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response


class DownloadDebitNote(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """

    filename = 'debitnote.pdf'
    template_name = 'admin/debitnote/debit_note.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))


        #order_obj1= get_object_or_404(OrderedProductMapping)
        pk=self.kwargs.get('pk')
        a = OrderedProduct.objects.get(pk=pk)
        products = a.rt_order_product_order_product_mapping.all()
        data = {"object": order_obj,"order": order_obj.order,"products":products }

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response

class CustomerCareApi(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        queryset = CustomerCare.objects.all()
        serializer = CustomerCareSerializer(queryset, many=True)
        msg = {'is_success': True, 'message': ['All Messages'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_201_CREATED)


    def post(self,request):
        phone_number = self.request.POST.get('phone_number')
        order_id=self.request.POST.get('order_id')
        select_issue=self.request.POST.get('select_issue')
        complaint_detail=self.request.POST.get('complaint_detail')
        msg = {'is_success': False,'message': [''],'response_data': None}
        if request.user.is_authenticated:
            phone_number = request.user.phone_number

        if not complaint_detail :
            msg['message']= ["Please type the complaint_detail"]
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        serializer = CustomerCareSerializer(data= {"phone_number":phone_number, "complaint_detail":complaint_detail, "order_id":order_id, "select_issue":select_issue})
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Message Sent'], 'response_data': serializer.data}
            return Response( msg, status=status.HTTP_201_CREATED)
        else:
            msg = {'is_success': False, 'message': ['Phone Number is not Valid'], 'response_data': None}
            return Response( msg, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomerOrdersList(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        #msg = {'is_success': True, 'message': ['No Orders of the logged in user'], 'response_data': None}
        #if request.user.is_authenticated:
            queryset = Order.objects.filter(ordered_by=request.user)
            if queryset.count()>0:
                serializer = OrderNumberSerializer(queryset, many=True)
                msg = {'is_success': True, 'message': ['All Orders of the logged in user'], 'response_data': serializer.data}
            else:
                serializer = OrderNumberSerializer(queryset, many=True)
                msg = {'is_success': False, 'message': ['No Orders of the logged in user'], 'response_data': None}
            return Response(msg, status=status.HTTP_201_CREATED)
        #else:
            #return Response(msg, status=status.HTTP_201_CREATED)

class PaymentApi(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request):
        queryset = Payment.objects.filter(payment_choice='cash_on_delivery')
        serializer = GramPaymentCodSerializer(queryset, many=True)
        msg = {'is_success': True, 'message': ['All Payments'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_201_CREATED)

    def post(self,request):
        order_id=self.request.POST.get('order_id')
        payment_choice =self.request.POST.get('payment_choice')
        paid_amount =self.request.POST.get('paid_amount')
        neft_reference_number =self.request.POST.get('neft_reference_number')
        shop_id = self.request.POST.get('shop_id')
        imei_no = self.request.POST.get('imei_no')

        # payment_type = neft or cash_on_delivery
        msg = {'is_success': False, 'message': ['Have some error in shop or mapping'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        if not payment_choice:
            msg['message'] = ["Please enter payment_type"]
            return Response(msg, status=status.HTTP_200_OK)
        else:
            if payment_choice =='neft' and not neft_reference_number:
                msg['message'] = ["Please enter neft_reference_number"]
                return Response(msg, status=status.HTTP_200_OK)

        if not paid_amount:
            msg['message'] = ["Please enter paid_amount"]
            return Response(msg, status=status.HTTP_200_OK)

        if parent_mapping.parent.shop_type.shop_type == 'sp':

            try:
                order = Order.objects.get(id=order_id)
            except ObjectDoesNotExist:
                msg['message'] = ["No order found"]
                return Response(msg, status=status.HTTP_200_OK)

            if Payment.objects.filter(order_id=order).exists():
                pass
            else:
                payment = Payment(order_id=order,paid_amount=paid_amount,payment_choice=payment_choice,
                              neft_reference_number=neft_reference_number,imei_no=imei_no)
                payment.save()
                order.order_status = 'opdp'
                order.save()
            serializer = OrderSerializer(order,context={'parent_mapping_id': parent_mapping.parent.id})

        elif parent_mapping.parent.shop_type.shop_type == 'gf':

            try:
                order = GramMappedOrder.objects.get(id=order_id)
            except ObjectDoesNotExist:
                msg['message'] = ["No order found"]
                return Response(msg, status=status.HTTP_200_OK)

            payment = GramMappedPayment(order_id=order,paid_amount=paid_amount,payment_choice=payment_choice,
                                        neft_reference_number=neft_reference_number,imei_no=imei_no)
            payment.save()
            order.order_status = 'opdp'
            order.save()
            serializer = GramMappedOrderSerializer(order,context={'parent_mapping_id': parent_mapping.parent.id})

        if serializer.data:
            msg = {'is_success': True,'message': None,'response_data': serializer.data}
        return Response( msg, status=status.HTTP_200_OK)


class ReleaseBlocking(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        shop_id = self.request.POST.get('shop_id')
        cart_id = self.request.POST.get('cart_id')
        msg = {'is_success': False, 'message': ['Have some error in shop or mapping'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        if not cart_id:
            msg['message'] = 'Cart id not found'
            return Response(msg, status=status.HTTP_200_OK)

        if parent_mapping.parent.shop_type.shop_type == 'sp':
            if OrderedProductReserved.objects.filter(cart__id=cart_id,reserve_status='reserved').exists():
                for ordered_reserve in OrderedProductReserved.objects.filter(cart__id=cart_id,reserve_status='reserved'):
                    ordered_reserve.order_product_reserved.available_qty = int(
                        ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
                    ordered_reserve.order_product_reserved.save()
                    ordered_reserve.delete()
            msg = {'is_success': True, 'message': ['Blocking has released'], 'response_data': None}
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            if GramOrderedProductReserved.objects.filter(cart__id=cart_id,reserve_status='reserved').exists():
                for ordered_reserve in GramOrderedProductReserved.objects.filter(cart__id=cart_id,reserve_status='reserved'):
                    ordered_reserve.order_product_reserved.available_qty = int(
                        ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
                    ordered_reserve.order_product_reserved.save()
                    ordered_reserve.delete()
            msg = {'is_success': True, 'message': ['Blocking has released'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

class DeliveryBoyTrips(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        trip_date = ('{}-{}-{}').format(kwargs['year'], kwargs['month'], kwargs['day'])
        trip = Trip.objects.filter(created_at__date=trip_date, delivery_boy=self.request.user)
        trip_details = TripSerializer(trip, many=True)
        msg = {'is_success': True, 'message': ['Trip Details'], 'response_data': trip_details.data}
        return Response(msg, status=status.HTTP_201_CREATED)

class DeliveryShipmentDetails(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        trip_id = kwargs.get('trip')
        trips = Trip.objects.get(id = trip_id , delivery_boy = self.request.user)
        shipments = trips.rt_invoice_trip.all()
        shipment_details = ShipmentSerializer(shipments, many=True)
        msg = {'is_success': True, 'message': ['Shipment Details'], 'response_data': shipment_details.data}
        return Response(msg, status=status.HTTP_201_CREATED)

class ShipmentDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        shipment = ShipmentProducts.objects.filter(ordered_product__id=shipment_id)
        shipment_product_details = ShipmentDetailSerializer(shipment, many=True)
        cash_to_be_collected = shipment.last().ordered_product.cash_to_be_collected()
        msg = {'is_success': True, 'message': ['Shipment Details'],
               'response_data': shipment_product_details.data,'cash_to_be_collected': cash_to_be_collected}
        return Response(msg, status=status.HTTP_201_CREATED)

    def post(self, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        shipment = ShipmentProducts.objects.filter(ordered_product__id=shipment_id)
        product = self.request.POST.get('product')
        returned_qty = self.request.POST.get('returned_qty')
        damaged_qty = self.request.POST.get('damaged_qty')
        msg = {'is_success': False,'message': [''],'response_data': None}

        datas = ShipmentProducts.objects.filter(ordered_product__id=shipment_id, product=product).update(returned_qty=returned_qty, damaged_qty=damaged_qty)
        serializer = ShipmentDetailSerializer(shipment, many=True)
        if serializer.data:
            cash_to_be_collected = shipment.last().ordered_product.cash_to_be_collected()
            msg = {'is_success': True, 'message': ['Shipment Details'], 'response_data': serializer.data, 'cash_to_be_collected': cash_to_be_collected}
            return Response( msg, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # else:
        #     msg = {'is_success': False, 'message': ['Phone Number is not Valid'], 'response_data': None}
        #     return Response( msg, status=status.HTTP_400_BAD_REQUEST)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FeedbackData(generics.ListCreateAPIView):
    serializer_class = FeedBackSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        ship_id = self.kwargs.get('ship_id')
        queryset = Feedback.objects.all()
        if ship_id:
            queryset = Feedback.objects.filter(shipment__id=ship_id)
        return queryset

    def create(self, request, *args, **kwargs):
        can_comment = False
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            if ((serializer.data['delivery_experience'] and int(serializer.data['delivery_experience']) > 4) or (serializer.data['overall_product_packaging'] and int(serializer.data['overall_product_packaging']) > 4)):
                can_comment = True
            msg = {'is_success': True, 'can_comment':can_comment, 'message': None, 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['shipment_id, user_id or status not found or value exists'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        feedback = serializer.save(user=self.request.user)
        return feedback

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True, 'message': [""], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class CancelOrder(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def put(self, request, format=None):
        try:
            order = Order.objects.get(buyer_shop__shop_owner=request.user,
                                      pk=request.data['order_id'])
        except ObjectDoesNotExist:
            msg = {'is_success': False,
                   'message': ['Order is not associated with the current user'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        serializer = CancelOrderSerializer(order, data=request.data,
                                           context={'order': order})
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True,
                    'message': ["Order Cancelled Successfully!"],
                    'response_data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)
        else:
            return format_serializer_errors(serializer.errors)

class RetailerShopsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        mobile_number = self.request.GET.get('mobile_number')
        msg = {'is_success': False, 'message': [''], 'response_data': None}
        User = get_user_model()
        try:
            user = User.objects.get(phone_number=mobile_number)
        except ObjectDoesNotExist:
            msg['message'] = ["No retailer exists with this number"]
            return Response(msg, status=status.HTTP_200_OK)
        shop_owner = User.objects.get(phone_number = mobile_number)
        sales_person_sp = Shop.objects.filter(related_users = self.request.user)
        shops = Shop.objects.filter(shop_owner = shop_owner, shop_type = 1)
        shops_list =[]
        for shop in shops:
            for parent in shop.retiler_mapping.all():
                if (parent.parent in sales_person_sp):
                    shops_list.append(shop)
                else:
                    return Response({"message":["The user is not mapped with the same service partner as the sales person"], "response_data": None ,"is_success": True, "is_user_mapped_with_same_sp": False})
        shops_serializer = RetailerShopSerializer(shops_list, many=True)
        if shops_list:
            return Response({"message":[""], "response_data": shops_serializer.data ,"is_success": True, "is_user_mapped_with_same_sp": True})
        else:
            return Response({"message":["The User is registered but does not have any shop"], "response_data": None ,"is_success": True, "is_user_mapped_with_same_sp": False})


class SellerOrderList(generics.ListAPIView):
    serializer_class = SellerOrderListSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        shop_emp = ShopUserMapping.objects.filter(employee=self.request.user, status=True)
        shop_mangr = ShopUserMapping.objects.filter(manager=self.request.user, status=True)
        if shop_emp.exists() and shop_emp.last().employee_group.permissions.filter(
                codename='can_sales_person_add_shop').exists():
            return shop_emp.values('shop')
        elif shop_mangr.exists():
            return shop_mangr.values('shop')

    def list(self, request, *args, **kwargs):
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
        current_url = request.get_host()
        queryset = Order.objects.filter(buyer_shop__in=self.get_queryset()).order_by('-created_at')
        users_list = [v['employee_id'] for v in self.get_queryset().values('employee_id')]
        serializer = SellerOrderListSerializer(queryset, many=True, context={'current_url':current_url, 'sales_person_list':users_list})
        if serializer.data:
            msg = {'is_success': True,'message': None,'response_data': serializer.data}
        return Response(msg,status=status.HTTP_200_OK)