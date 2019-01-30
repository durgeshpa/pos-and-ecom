from rest_framework import generics
from .serializers import (ProductsSearchSerializer,GramGRNProductsSearchSerializer,CartProductMappingSerializer,CartSerializer,
                          OrderSerializer, CustomerCareSerializer, OrderNumberSerializer, PaymentCodSerializer,PaymentNeftSerializer,GramPaymentCodSerializer,GramPaymentNeftSerializer,

                          GramMappedCartSerializer,GramMappedOrderSerializer,ProductDetailSerializer )
from products.models import Product, ProductPrice, ProductOption,ProductImage
from sp_to_gram.models import OrderedProductMapping,OrderedProductReserved

from rest_framework import permissions, authentication
from gram_to_brand.models import (GRNOrderProductMapping, CartProductMapping as GramCartProductMapping,
                                  OrderedProductReserved as GramOrderedProductReserved, PickList, PickListItems )
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from retailer_to_sp.models import Cart,CartProductMapping,Order,OrderedProduct, Payment, CustomerCare

from retailer_to_gram.models import ( Cart as GramMappedCart,CartProductMapping as GramMappedCartProductMapping,Order as GramMappedOrder,
                                      OrderedProduct as GramOrderedProduct, Payment as GramMappedPayment, CustomerCare as GramMappedCustomerCare )


from shops.models import Shop,ParentRetailerMapping
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F,Sum
from wkhtmltopdf.views import PDFTemplateResponse
from django.shortcuts import get_object_or_404, get_list_or_404
from datetime import datetime, timedelta
from django.utils import timezone
from products.models import ProductCategory
from addresses.models import Address
from retailer_backend.common_function import getShopMapping,checkNotShopAndMapping,getShop

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
        brand = request.data.get('brands')
        category = request.data.get('categories')
        keyword = request.data.get('product_name', None)
        shop_id = request.data.get('shop_id')
        cart_check = False
        is_store_active = True
        sort_preference = request.data.get('sort_by_price')
        grn = GRNOrderProductMapping.objects.values('product_id')
        products = Product.objects.filter(pk__in=grn).order_by('product_name')
        if brand:
            products = products.filter(product_brand__in=brand)
        if category:
            product_ids = ProductCategory.objects.filter(product__in=grn, category__in=category).values_list('product_id')
            products = products.filter(pk__in=product_ids)
        if keyword and products.filter(product_name__icontains=keyword).last():
            products = products.filter(product_name__icontains=keyword)

        products_price = ProductPrice.objects.filter(product__in=products).order_by('product','-created_at').distinct('product')
        if sort_preference:
            if sort_preference == 'low':
                products_price = products_price.order_by('price_to_retailer').distinct()
            if sort_preference == 'high':
                products_price = products_price.order_by('-price_to_retailer').distinct()
        try:
            shop = Shop.objects.get(id=shop_id,status=True)
        except ObjectDoesNotExist:
            message = "Shop not active or does not exists"
            is_store_active = False
        else:
            try:
                parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
            except ObjectDoesNotExist:
                message = "Shop Mapping Not Found"
                is_store_active = False
            else:
                products_price = products_price.filter(shop=parent_mapping.parent)
            # if shop mapped with sp
            if parent_mapping.parent.shop_type.shop_type == 'sp':
                cart = Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).last()
                if cart:
                    cart_products = cart.rt_cart_list.all()
                    cart_check = True
            # if shop mapped with gf
            elif parent_mapping.parent.shop_type.shop_type == 'gf':
                cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                 cart_status__in=['active', 'pending']).last()
                if cart:
                    cart_products = cart.rt_cart_list.all()
                    cart_check = True

        p_list = []

        for p in products_price:
            user_selected_qty = None
            if cart_check == True:
                for c_p in cart_products:
                    if c_p.cart_product_id == p.product_id:
                        user_selected_qty = c_p.qty
            name = p.product.product_name
            mrp = p.mrp
            ptr = p.price_to_retailer
            status = p.product.status
            product_opt = p.product.product_opt_product.all()
            weight_value = None
            weight_unit = None
            pack_size = None
            try:
                pack_size = p.product.product_inner_case_size if p.product.product_inner_case_size else None
            except:
                pack_size = None
            try:
                for p_o in product_opt:
                    weight_value = p_o.weight.weight_value if p_o.weight.weight_value else None
                    weight_unit = p_o.weight.weight_unit if p_o.weight.weight_unit else None
            except:
                weight_value = None
                weight_unit = None
            product_img = p.product.product_pro_image.all()
            product_images = [
                                {
                                    "image_name":p_i.image_name,
                                    "image_alt":p_i.image_alt_text,
                                    "image_url":p_i.image.url
                                }
                                for p_i in product_img
                            ]
            if not product_images:
                product_images=None
            if request.user.is_authenticated:
                p_list.append({"name":p.product.product_name, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "id":p.product_id,
                                "weight_value":weight_value,"weight_unit":weight_unit,"product_images":product_images,"user_selected_qty":user_selected_qty})
            else:
                is_store_active = False
                p_list.append({"name":p.product.product_name, "mrp":None, "ptr":None, "status":status, "pack_size":pack_size, "id":p.product_id,
                                "weight_value":weight_value,"weight_unit":weight_unit,"product_images":product_images,"user_selected_qty":None})

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
                    cart.save()
                else:
                    cart = Cart(last_modified_by=self.request.user, cart_status='active')
                    cart.save()

                if int(qty) == 0:
                    if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                        CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

                else:
                    cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                    cart_mapping.qty = qty
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

    def get(self,request,*args,**kwargs):
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
                    serializer = CartSerializer(Cart.objects.get(id=cart.id))
                    msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
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
                    serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id),context={'parent_mapping_id': parent_mapping.parent.id})
                    msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
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
        msg = {'is_success': False, 'message': ['No any product available in this cart'], 'response_data': None}

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
                cart_products = CartProductMapping.objects.filter(cart=cart)

                for cart_product in cart_products:
                    ordered_product_details = OrderedProductMapping.objects.filter(
                        ordered_product__order__shipping_address__shop_name=parent_mapping.parent,
                        product=cart_product.cart_product).order_by('-expiry_date')
                    ordered_product_sum = ordered_product_details.aggregate(available_qty_sum=Sum('available_qty'))

                    if ordered_product_sum['available_qty_sum'] is not None:
                        if int(ordered_product_sum['available_qty_sum']) < int(cart_product.qty):
                            available_qty = int(ordered_product_sum['available_qty_sum'])
                            cart_product.qty_error_msg = 'Available Quantity : %s' % (available_qty)
                            # cart_product.qty = available_qty
                        else:
                            available_qty = int(cart_product.qty)
                            cart_product.qty_error_msg = ''

                        cart_product.save()

                        for product_detail in ordered_product_details:
                            if available_qty <= 0:
                                break

                            product_detail.available_qty = 0 if available_qty > product_detail.available_qty else int(
                                product_detail.available_qty) - int(available_qty)
                            product_detail.save()

                            order_product_reserved = OrderedProductReserved(product=product_detail.product,
                                                                            reserved_qty=available_qty)
                            order_product_reserved.order_product_reserved = product_detail
                            order_product_reserved.cart = cart
                            order_product_reserved.reserve_status = 'reserved'
                            order_product_reserved.save()

                            available_qty = available_qty - int(product_detail.available_qty)

                        serializer = CartSerializer(cart,context={'parent_mapping_id': parent_mapping.parent.id})
                        msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                    else:
                        msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                        return Response(msg, status=status.HTTP_200_OK)
                if CartProductMapping.objects.filter(cart=cart).count() <= 0:
                    msg = {'is_success': False, 'message': ['No any product available ins this cart'],
                           'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with gf
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            if GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                             cart_status__in=['active', 'pending']).exists():
                cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                     cart_status__in=['active', 'pending']).last()
                cart_products = GramMappedCartProductMapping.objects.filter(cart=cart)
                pick_list,_ = PickList.objects.get_or_create(cart=cart)
                pick_list.save()

                for cart_product in cart_products:
                    ordered_product_details = GRNOrderProductMapping.objects.filter(
                        grn_order__order__shipping_address__shop_name=parent_mapping.parent,
                        product=cart_product.cart_product).order_by('-expiry_date')
                    ordered_product_sum = ordered_product_details.aggregate(available_qty_sum=Sum('available_qty'))

                    if ordered_product_sum['available_qty_sum'] is not None:
                        if int(ordered_product_sum['available_qty_sum']) < int(cart_product.qty):
                            available_qty = int(ordered_product_sum['available_qty_sum'])
                            cart_product.qty_error_msg = 'Available Quantity : %s' % (available_qty)
                        else:
                            available_qty = int(cart_product.qty)
                            cart_product.qty_error_msg = ''

                        cart_product.save()

                        for product_detail in ordered_product_details:
                            if available_qty <= 0:
                                break

                            product_detail.available_qty = 0 if available_qty > product_detail.available_qty else int(
                                product_detail.available_qty) - int(available_qty)
                            product_detail.save()

                            order_product_reserved_dt = GramOrderedProductReserved(product=product_detail.product,
                                                                                reserved_qty=available_qty)
                            order_product_reserved_dt.order_product_reserved = product_detail
                            order_product_reserved_dt.cart = cart
                            order_product_reserved_dt.reserve_status = 'reserved'
                            order_product_reserved_dt.save()

                            pick_list_item = PickListItems(pick_list=pick_list, grn_order=product_detail.grn_order,
                                                           pick_qty=available_qty)
                            pick_list_item.product = product_detail.product
                            pick_list_item.save()
                            available_qty = available_qty - int(product_detail.available_qty)

                        serializer = GramMappedCartSerializer(cart, context={'parent_mapping_id': parent_mapping.parent.id})
                        msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                    else:
                        msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                        return Response(msg, status=status.HTTP_200_OK)
                if GramMappedCartProductMapping.objects.filter(cart=cart).count() <= 0:
                    msg = {'is_success': False, 'message': ['No any product available ins this cart'],
                           'response_data': None}
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

        total_mrp = self.request.POST.get('total_mrp',0)
        total_tax_amount = self.request.POST.get('total_tax_amount',0)
        total_final_amount = self.request.POST.get('total_final_amount',0)

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

        # if shop mapped with sp
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            #self.sp_mapping_order_reserve()
            if Cart.objects.filter(last_modified_by=self.request.user, id=cart_id).exists():
                cart = Cart.objects.get(last_modified_by=self.request.user, id=cart_id)
                cart.cart_status = 'ordered'
                cart.save()

                if OrderedProductReserved.objects.filter(cart=cart).exists():
                    order,_ = Order.objects.get_or_create(last_modified_by=request.user,ordered_by=request.user, ordered_cart=cart, order_no=cart.order_id)

                    order.billing_address = billing_address
                    order.shipping_address = shipping_address
                    order.buyer_shop = shop
                    order.seller_shop = parent_mapping.parent

                    order.total_mrp = float(total_mrp)
                    order.total_tax_amount = float(total_tax_amount)
                    order.total_final_amount = float(total_final_amount)

                    order.order_status = 'ordered'
                    order.save()

                    # Remove Data From OrderedProductReserved
                    for ordered_reserve in OrderedProductReserved.objects.filter(cart=cart):
                        ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
                        ordered_reserve.order_product_reserved.save()
                        ordered_reserve.reserve_status = 'ordered'
                        ordered_reserve.save()

                    serializer = OrderSerializer(order,context={'parent_mapping_id': parent_mapping.parent.id})
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

                    order.total_mrp = float(total_mrp)
                    order.total_tax_amount = float(total_tax_amount)
                    order.total_final_amount = float(total_final_amount)

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

                    serializer = GramMappedOrderSerializer(order,context={'parent_mapping_id': parent_mapping.parent.id})
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
    serializer_class = OrderSerializer
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

        if parent_mapping.parent.shop_type.shop_type == 'sp':
            queryset = Order.objects.filter(last_modified_by=user).order_by('-created_at')
            serializer = OrderSerializer(queryset, many=True, context={'parent_mapping_id': parent_mapping.parent.id})
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            queryset = GramMappedOrder.objects.filter(last_modified_by=user).order_by('-created_at')
            serializer = GramMappedOrderSerializer(queryset, many=True, context={'parent_mapping_id': parent_mapping.parent.id})

        if serializer.data:
            msg = {'is_success': True,'message': None,'response_data': serializer.data}
        return Response(msg,status=status.HTTP_200_OK)

class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
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

        if parent_mapping.parent.shop_type.shop_type == 'sp':
            queryset = Order.objects.get(id=pk)
            serializer = OrderSerializer(queryset, context={'parent_mapping_id': parent_mapping.parent.id})
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            queryset = GramMappedOrder.objects.get(id=pk)
            serializer = GramMappedOrderSerializer(queryset,context={'parent_mapping_id': parent_mapping.parent.id})

        if serializer.data:
            msg = {'is_success': True,'message': None,'response_data': serializer.data}
        return Response(msg,status=status.HTTP_200_OK)

class DownloadInvoiceSP(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'invoice.pdf'
    template_name = 'admin/invoice/invoice.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))

        #order_obj1= get_object_or_404(OrderedProductMapping)
        pk=self.kwargs.get('pk')
        a = OrderedProduct.objects.get(pk=pk)
        print(a)
        shop=a
        products = a.rt_order_product_order_product_mapping.all()

        order_id= a.order.order_no

        sum_qty = 0
        sum_amount=0
        tax_inline=0
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
            
        for m in products:

            sum_qty = sum_qty + int(m.product.product_inner_case_size) * int(m.shipped_qty)

            for h in m.product.product_pro_price.all():

                sum_amount = sum_amount + (m.shipped_qty * h.price_to_retailer)
                inline_sum_amount = (m.shipped_qty * h.price_to_retailer)
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
            print(surcharge_tax_list)
            print(gst_tax_list)
            print(cess_tax_list)
            print(taxes_list)

        total_amount = sum_amount
        print(sum_amount)


        data = {"object": order_obj,"order": order_obj.order,"products":products ,"shop":shop, "sum_qty": sum_qty, "sum_amount":sum_amount,"url":request.get_host(), "scheme": request.is_secure() and "https" or "http" , "igst":igst, "cgst":cgst,"sgst":sgst,"cess":cess,"surcharge":surcharge, "total_amount":total_amount,"order_id":order_id,"shop_name_gram":shop_name_gram,"nick_name_gram":nick_name_gram, "city_gram":city_gram, "address_line1_gram":address_line1_gram, "pincode_gram":pincode_gram,"state_gram":state_gram}

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

    def get(self, request):
        queryset = CustomerCare.objects.all()
        serializer = CustomerCareSerializer(queryset, many=True)
        msg = {'is_success': True, 'message': ['All Messages'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_201_CREATED)


    def post(self,request):
        #import pdb; pdb.set_trace()
        #msg = {'is_success': False,'message': ['Sorry no message entered!'],'response_data': None}
        order_id=self.request.POST.get('order_id')
        select_issue=self.request.POST.get('select_issue')
        complaint_detail=self.request.POST.get('complaint_detail')
        msg = {'is_success': False,'message': [''],'response_data': None}

        try:
            order = GramMappedOrder.objects.get(id=order_id)
        except ObjectDoesNotExist:
            msg['message'] = ["No order with this name"]
            return Response(msg, status=status.HTTP_200_OK)

        if not select_issue :
            msg['message']= ["Please select the issue"]
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        if not complaint_detail :
            msg['message']= ["Please typle the complaint_detail"]
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        print(request.data)
        serializer = CustomerCareSerializer(data=request.data)
        if serializer.is_valid():
            print("mmk")
            serializer.save()
            msg = {'is_success': True, 'message': ['Message Sent'], 'response_data': serializer.data}
            return Response( msg, status=status.HTTP_201_CREATED)
        #return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomerOrdersList(APIView):

    def get(self, request):
        #msg = {'is_success': True, 'message': ['No Orders of the logged in user'], 'response_data': None}
        #if request.user.is_authenticated:
            queryset = GramMappedOrder.objects.filter(ordered_by=request.user)
            serializer = OrderNumberSerializer(queryset, many=True)
            msg = {'is_success': True, 'message': ['All Orders of the logged in user'], 'response_data': serializer.data}
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

            payment = Payment(order_id=order,paid_amount=paid_amount,payment_choice=payment_choice,neft_reference_number=neft_reference_number)
            payment.save()
            order.order_status = 'payment_done_approval_pending'
            order.save()
            serializer = OrderSerializer(order,context={'parent_mapping_id': parent_mapping.parent.id})

        elif parent_mapping.parent.shop_type.shop_type == 'gf':

            try:
                order = GramMappedOrder.objects.get(id=order_id)
            except ObjectDoesNotExist:
                msg['message'] = ["No order found"]
                return Response(msg, status=status.HTTP_200_OK)

            payment = GramMappedPayment(order_id=order,paid_amount=paid_amount,payment_choice=payment_choice,neft_reference_number=neft_reference_number)
            payment.save()
            order.order_status = 'payment_done_approval_pending'
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


