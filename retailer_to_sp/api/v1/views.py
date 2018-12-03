from rest_framework import generics
from .serializers import (ProductsSearchSerializer,GramGRNProductsSearchSerializer,CartProductMappingSerializer,CartSerializer,
                          OrderSerializer, CustomerCareSerializer, OrderNumberSerializer, PaymentCodSerializer,PaymentNeftSerializer,

                          GramMappedCartSerializer,GramMappedOrderSerializer )
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
from retailer_to_sp.models import Cart,CartProductMapping,Order,OrderedProduct, Payment
from retailer_to_gram.models import ( Cart as GramMappedCart,CartProductMapping as GramMappedCartProductMapping,Order as GramMappedOrder,
                                      OrderedProduct as GramOrderedProduct)


from shops.models import Shop,ParentRetailerMapping
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F,Sum
from wkhtmltopdf.views import PDFTemplateResponse
from django.shortcuts import get_object_or_404, get_list_or_404
from datetime import datetime, timedelta
from django.utils import timezone
from products.models import ProductCategory
from addresses.models import Address

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

# class GramGRNProductsList(APIView):
#     permission_classes = (AllowAny,)
#     serializer_class = GramGRNProductsSearchSerializer
#
#     def post(self, request, format=None):
#         import pdb; pdb.set_trace()
#         grn = GRNOrderProductMapping.objects.all()
#         #grn = OrderedProductMapping.objects.all()
#         p_id_list = []
#         for p in grn:
#             product = p.product
#             id = product.pk
#             p_id_list.append(id)
#         products = Product.objects.filter(pk__in=p_id_list)
#         p_list = []
#         msg = {'is_success': False, 'message': ['Sorry no product found!'], 'response_data': None}
#         for product in products:
#             id = product.pk
#             name = product.product_name
#
#             try:
#                 product_price = ProductPrice.objects.get(product=product)
#             except ObjectDoesNotExist:
#                 msg['message'] = ['Product id %s  and name %s have price not found '%(product.id, product.product_name)]
#                 return Response(msg, status=400)
#
#             try:
#                 product_option = ProductOption.objects.filter(product=product)[0]
#             except ObjectDoesNotExist:
#                 msg['message'] = ['Product id %s  and name %s have product_option not found '%(product.id, product.product_name)]
#                 return Response(msg, status=400)
#
#             try:
#                 product_image = ProductImage.objects.filter(product=product)
#             except ObjectDoesNotExist:
#                 msg['message'] = ['Product id %s  and name %s have product_image not found '%(product.id, product.product_name)]
#                 return Response(msg, status=400)
#
#             mrp = product_price.mrp
#             ptr = product_price.price_to_retailer
#             status = product_price.status
#
#             pack_size = product_option.package_size.pack_size_name
#             weight_value = product_option.weight.weight_value
#             weight_unit = product_option.weight.weight_unit
#             weight = product_option.weight.weight_name
#
#             #image = product_image.image.url
#
#             if name.startswith(request.data['product_name']):
#                 p_list.append({"name":name, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "weight":weight, "id":id,
#                                "weight_value":weight_value,"weight_unit":weight_unit})
#         if not p_list:
#             return Response(msg,status=400)
#
#         msg = {'is_success': True,
#                 'message': ['Products found'],
#                 'response_data':p_list }
#         return Response(msg,
#                         status=200)

class GramGRNProductsList(APIView):
    permission_classes = (AllowAny,)
    serializer_class = GramGRNProductsSearchSerializer

    def post(self, request, format=None):
        grn = GRNOrderProductMapping.objects.values('product_id')
        products_price = ProductPrice.objects.filter(product__in=grn).order_by('product','-created_at').distinct('product')
        msg = {'is_success': False,'message': ['Sorry no any mapping with any shop!'],'response_data': None}
        if 'brands' in request.data and request.data['brands'] and not request.data['categories']:
            products = Product.objects.filter(pk__in=grn, product_brand__in=request.data['brands']).values_list('pk')
            products_price = ProductPrice.objects.filter(product__in=products).order_by('product','-created_at').distinct('product')

        if 'categories' in request.data and request.data['categories'] and not request.data['brands']:
            products = ProductCategory.objects.filter(product__in=grn, category__in=request.data['categories']).values_list('product_id')
            products_price = ProductPrice.objects.filter(product__in=products).order_by('product','-created_at').distinct('product')

        if 'categories' and 'brands' in request.data:
            if request.data['brands'] and request.data['categories']:
                products_by_brand = Product.objects.filter(pk__in=grn, product_brand__in=request.data['brands']).values_list('pk')
                products_by_category = products = ProductCategory.objects.filter(product__in=grn, category__in=request.data['categories']).values_list('product_id')
                from itertools import chain
                products = list(chain(products_by_brand,products_by_category))
                products_price = ProductPrice.objects.filter(product__in=products).order_by('product','-created_at').distinct('product')

        if 'sort_by_price' in request.data and request.data['sort_by_price'] == 'low':
            products_price = products_price.order_by('price_to_retailer').distinct()

        if 'sort_by_price' in request.data and request.data['sort_by_price'] == 'high':
            products_price = products_price.order_by('-price_to_retailer').distinct()

        if request.user.is_authenticated:
            # get shop
            try:
                if not 'shop_id' in request.data:
                    msg['message'] = ["Shop ID is required"]
                    return Response(msg, status=200)
                else:
                    try:
                        shop_id = int(request.data['shop_id'])
                    except ValueError:
                        msg['message'] = ["shop_id should be an integer value"]
                        return Response(msg, status=200)
                shop = Shop.objects.get(id=request.data['shop_id'])
            except ObjectDoesNotExist:
                msg['message'] = ["Shop not Found"]
                return Response(msg, status=200)

            # get parent mapping
            try:
                parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
            except ObjectDoesNotExist:
                msg['message'] = ["Shop Mapping Not Found"]
                return Response(msg, status=200)
            # if shop mapped with sp
            if parent_mapping.parent.shop_type.shop_type == 'sp':
                if Cart.objects.filter(last_modified_by=self.request.user, cart_status='active').exists():
                    cart = Cart.objects.filter(last_modified_by=self.request.user,
                                               cart_status='active').last()
                    cart_products = CartProductMapping.objects.filter(cart__in=carts)

            # if shop mapped with gf
            elif parent_mapping.parent.shop_type.shop_type == 'gf':
                if GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                 cart_status='active').exists():
                    cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                         cart_status='active').last()
                    cart_products = GramMappedCartProductMapping.objects.filter(cart__in=carts)

            else:
                msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],'response_data': None}
                return Response(msg, status=200)

            p_list = []

            for p in products_price:
                product_images = []
                user_selected_qty = None
                for c_p in cart_products:
                    if c_p.cart_product_id == p.product_id:
                        user_selected_qty = c_p.qty
                id = p.product_id
                name = p.product.product_name
                mrp = p.mrp
                ptr = p.price_to_retailer
                status = p.product.status
                product_opt = p.product.product_opt_product.all()
                pack_size = p.product.product_inner_case_size if p.product.product_inner_case_size else None
                weight_value = None
                weight_unit = None
                for p_o in product_opt:
                    weight_value = p_o.weight.weight_value if p_o.weight.weight_value else None
                    weight_unit = p_o.weight.weight_unit if p_o.weight.weight_unit else None
                product_img = p.product.product_pro_image.all()
                for p_i in product_img:
                    product_images.append({"image_name":p_i.image_name,"image_alt":p_i.image_alt_text,"image_url":p_i.image.url})
                if not product_images:
                    product_images=None
                if name.startswith(request.data['product_name']):
                    p_list.append({"name":name, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "id":id,
                                    "weight_value":weight_value,"weight_unit":weight_unit,"product_images":product_images,"user_selected_qty":user_selected_qty})
        else:
            p_list = []
            for p in products_price:
                product_images = []
                user_selected_qty = None
                id = p.product_id
                name = p.product.product_name
                mrp = None
                ptr = None
                status = p.product.status
                product_opt = p.product.product_opt_product.all()
                pack_size = p.product.product_inner_case_size if p.product.product_inner_case_size else None
                weight_value = None
                weight_unit = None
                for p_o in product_opt:
                    weight_value = p_o.weight.weight_value if p_o.weight.weight_value else None
                    weight_unit = p_o.weight.weight_unit if p_o.weight.weight_unit else None
                product_img = p.product.product_pro_image.all()
                for p_i in product_img:
                    product_images.append({"image_name":p_i.image_name,"image_alt":p_i.image_alt_text,"image_url":p_i.image.url})
                if not product_images:
                    product_images=None
                if name.startswith(request.data['product_name']):
                    p_list.append({"name":name, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "id":id,
                                "weight_value":weight_value,"weight_unit":weight_unit, "product_images":product_images,"user_selected_qty":user_selected_qty})

        msg = {'is_success': True,
                 'message': ['Products found'],
                 'response_data':p_list }
        if not p_list:
            msg = {'is_success': False,
                     'message': ['Sorry! No product found'],
                     'response_data':None }
        return Response(msg,
                         status=200)

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

            # get parent mapping
            try:
                parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
            except ObjectDoesNotExist:
                msg['message'] = ["Shop Mapping Not Found"]
                return Response(msg, status=status.HTTP_200_OK)

            # if qty not found or less then zero then
            if not qty or int(qty) < 0:
                msg['message'] = ["Please enter the quantity greater than zero"]
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
            print("anc1")

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
                    serializer = CartSerializer(Cart.objects.get(id=cart.id))
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
                    serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id))
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
        msg = {'is_success': False, 'message': ['Sorry card detail not found'], 'response_data': None}

        # get shop
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop Not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        # get parent mapping
        try:
            parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop Mapping Not Found"]
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
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],'response_data': None}
                else:
                    serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id))
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
        # get shop
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop Not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        # get parent mapping
        try:
            parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop Mapping Not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with sp
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            if Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).exists():
                cart = Cart.objects.filter(last_modified_by=self.request.user,
                                           cart_status__in=['active', 'pending']).last()
                cart_products = CartProductMapping.objects.filter(cart=cart)

                for cart_product in cart_products:
                    ordered_product_details = OrderedProductMapping.objects.filter(
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

                        # if int(available_qty) == 0:
                        #     cart_product.delete()
                        # else:
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
                            order_product_reserved.save()

                            available_qty = available_qty - int(product_detail.available_qty)

                        serializer = CartSerializer(cart)
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
                            order_product_reserved_dt.save()

                            pick_list_item = PickListItems(pick_list=pick_list, grn_order=product_detail.grn_order,
                                                           pick_qty=available_qty)
                            pick_list_item.product = product_detail.product
                            pick_list_item.save()
                            available_qty = available_qty - int(product_detail.available_qty)

                        serializer = GramMappedCartSerializer(cart)
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
        msg = {'is_success': False, 'message': ['Cart is none'], 'response_data': None}

        #get shop
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop not Found"]
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

        # get parent mapping
        try:
            parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop Mapping Not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with sp
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            #self.sp_mapping_order_reserve()
            if Cart.objects.filter(last_modified_by=self.request.user, id=cart_id).exists():
                cart = Cart.objects.get(last_modified_by=self.request.user, id=cart_id)
                cart.cart_status = 'ordered'
                cart.save()

                if OrderedProductReserved.objects.filter(cart=cart).exists():
                    order = Order.objects.get_or_create(last_modified_by=request.user, ordered_cart=cart, order_no=cart.order_id)

                    order.billing_address = billing_address
                    order.shipping_address = shipping_address
                    order.buyer_shop = shop

                    order.total_mrp = float(total_mrp)
                    order.total_tax_amount = float(total_tax_amount)
                    order.total_final_amount = float(total_final_amount)

                    order.order_status = 'ordered'
                    order.save()

                    # pick_list = PickList.objects.get(cart=cart)
                    # pick_list.order = order
                    # pick_list.save()

                    # Remove Data From OrderedProductReserved
                    for ordered_reserve in OrderedProductReserved.objects.filter(cart=cart):
                        ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
                        ordered_reserve.order_product_reserved.save()
                        ordered_reserve.delete()

                    serializer = OrderSerializer(order)
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
                    order,_ = GramMappedOrder.objects.get_or_create(last_modified_by=request.user, ordered_cart=cart, order_no=cart.order_id)

                    order.billing_address = billing_address
                    order.shipping_address = shipping_address
                    order.buyer_shop = shop

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
                        ordered_reserve.delete()

                    serializer = GramMappedOrderSerializer(order)
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


    def get_queryset(self):
        user = self.request.user
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}

        # get shop
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        # get parent mapping
        try:
            parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop Mapping Not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        if parent_mapping.parent.shop_type.shop_type == 'sp':
            return Order.objects.filter(last_modified_by=user)
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            return GramMappedOrder.objects.filter(last_modified_by=user)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        if serializer.data:
            msg = {'is_success': True,
                    'message': None,
                    'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
        return Response(msg,status=status.HTTP_200_OK)

class OrderDetail(generics.ListAPIView):
    serializer_class = OrderSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self,*args,**kwargs):
        pk = self.kwargs.get('pk')
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}

        # get shop
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        # get parent mapping
        try:
            parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
        except ObjectDoesNotExist:
            msg['message'] = ["Shop Mapping Not Found"]
            return Response(msg, status=status.HTTP_200_OK)

        if parent_mapping.parent.shop_type.shop_type == 'sp':
            return Order.objects.filter(last_modified_by=self.request.user)
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            return GramMappedOrder.objects.filter(last_modified_by=self.request.user)


    def list(self, request, pk):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        if serializer.data:
            msg = {'is_success': True,
                    'message': None,
                    'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
        return Response(msg,
                        status=status.HTTP_200_OK)

class DownloadInvoice(APIView):
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

        products = a.rt_order_product_order_product_mapping.all()
        data = {"object": order_obj,"order": order_obj.order,"products":products }

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
            order = Order.objects.get(id=order_id)
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
            queryset = Order.objects.filter(ordered_by=request.user)
            serializer = OrderNumberSerializer(queryset, many=True)
            msg = {'is_success': True, 'message': ['All Orders of the logged in user'], 'response_data': serializer.data}
            return Response(msg, status=status.HTTP_201_CREATED)
        #else:
            #return Response(msg, status=status.HTTP_201_CREATED)

class PaymentCodApi(APIView):

    def get(self, request):
        queryset = Payment.objects.filter(payment_choice='cash_on_delivery')
        serializer = PaymentCodSerializer(queryset, many=True)
        msg = {'is_success': True, 'message': ['All Payments'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_201_CREATED)

    def post(self,request):

        order_id=self.request.POST.get('order_id')
        paid_amount=self.request.POST.get('paid_amount')
        #payment_choice=self.request.POST.get('payment_choice')
        msg = {'is_success': False,'message': [''],'response_data': None}

        try:
            order = Order.objects.get(id=order_id)
        except ObjectDoesNotExist:
            msg['message'] = ["No order with this name"]
            return Response(msg, status=status.HTTP_200_OK)

        if not paid_amount :
            msg['message']= ["Please enter the amount to be paid"]
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        #print(request.data)
        serializer = PaymentCodSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(payment_choice='cash_on_delivery')
            msg = {'is_success': True, 'message': ['Payment Sent'], 'response_data': serializer.data}
            return Response( msg, status=status.HTTP_201_CREATED)

class PaymentNeftApi(APIView):

    def get(self, request):
        queryset = Payment.objects.filter(payment_choice='neft')
        serializer = PaymentNeftSerializer(queryset, many=True)
        msg = {'is_success': True, 'message': ['All Payments'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_201_CREATED)

    def post(self,request):

        order_id=self.request.POST.get('order_id')
        paid_amount=self.request.POST.get('paid_amount')
        #payment_choice=self.request.POST.get('payment_choice')
        neft_reference_number=self.request.POST.get('neft_reference_number')
        msg = {'is_success': False,'message': [''],'response_data': None}

        try:
            order = Order.objects.get(id=order_id)
        except ObjectDoesNotExist:
            msg['message'] = ["No order with this name"]
            return Response(msg, status=status.HTTP_200_OK)
        if not paid_amount :
            msg['message']= ["Please enter the amount to be paid"]
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        if not neft_reference_number:
            msg['message']= ["Please select the NEFT reference numner"]
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        #print(request.data)
        serializer = PaymentNeftSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(payment_choice='neft')
            msg = {'is_success': True, 'message': ['Payment Sent'], 'response_data': serializer.data}
            return Response( msg, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
