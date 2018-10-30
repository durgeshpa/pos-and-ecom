from rest_framework import generics
from .serializers import (ProductsSearchSerializer,GramGRNProductsSearchSerializer,CartProductMappingSerializer,CartSerializer,OrderSerializer)
from products.models import Product, ProductPrice, ProductOption
from sp_to_gram.models import OrderedProductMapping,OrderedProductReserved


from gram_to_brand.models import GRNOrderProductMapping, Address
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from retailer_to_sp.models import Cart,CartProductMapping,Order,OrderedProduct
from shops.models import Shop
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F,Sum
from wkhtmltopdf.views import PDFTemplateResponse
from django.shortcuts import get_object_or_404, get_list_or_404

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


class AddToCart(APIView):

    def post(self,request):
        cart_product = self.request.POST.get('cart_product')
        qty = self.request.POST.get('qty')
        msg = {'is_success': False,'message': ['Sorry no any mapping with any shop!'],'response_data': None}

        if Shop.objects.filter(shop_owner=request.user).exists():
            if Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).exists():
                cart = Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).last()
                cart.cart_status = 'active'
                cart.save()
            else:
                cart = Cart(last_modified_by=self.request.user,cart_status='active')
                cart.save()

            try:
                product = Product.objects.get(id=cart_product)
            except ObjectDoesNotExist:
                msg['message'] = ["Product not Found"]
                return Response(msg, status=status.HTTP_200_OK)

            if not qty or int(qty) < 0:
                msg['message']= ["Please enter the quantity greater than zero"]
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)


            if int(qty) == 0:
                if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                    CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

            else:
                cart_mapping,_ =CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                cart_mapping.qty = qty
                cart_mapping.save()

            #serializer = CartProductMappingSerializer(CartProductMapping.objects.get(id=cart_mapping.id))
            serializer = CartSerializer(Cart.objects.get(id=cart.id))
            msg = {'is_success': True, 'message': ['Data added to cart'], 'response_data': serializer.data}
            return Response(msg, status=status.HTTP_201_CREATED)
            #return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(msg,status=status.HTTP_200_OK)


class CartDetail(APIView):

    def get(self,request,*args,**kwargs):
        if Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).exists():
            cart = Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).last()
            serializer = CartSerializer(Cart.objects.get(id=cart.id))
            msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)
        else:
            msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'], 'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)


class ReservedOrder(generics.ListAPIView):

    def post(self, request):
        if Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).exists():
            cart = Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).last()
            #cart_products = CartProductMapping.objects.filter(cart=cart).values('cart_product','qty')
            cart_products = CartProductMapping.objects.filter(cart=cart)
            error = []
            msg = []
            for cart_product in cart_products:
                print(cart_product)
                #print(cart_product['cart_product'])

                ordered_product_details = OrderedProductMapping.objects.filter(product=cart_product.cart_product).order_by('-expiry_date')
                ordered_product_sum = ordered_product_details.aggregate(available_qty_sum=Sum('available_qty'))
                #available_qty = product_details['available_qty'] if product_details['available_qty'] < cart_product['qty'] else cart_product['qty']
                #error[cart_product['cart_product']] = '' if product_details['available_qty'] < cart_product['qty'] else 'Product is not avilable of that much quantity'
                #cart_product['qty'] = available_qty

                #print(ordered_product_details)
                #print(ordered_product_details['available_qty_sum'])

                if ordered_product_sum['available_qty_sum'] is not None:
                    if int(ordered_product_sum['available_qty_sum']) < int(cart_product.qty):
                        available_qty = int(ordered_product_sum['available_qty_sum'])
                        cart_product.qty_error_msg ='Product is not available of that much quantity'
                        cart_product.qty = available_qty

                    else:
                        available_qty = int(cart_product.qty)
                        #cart_product['qty'] = product_details['available_qty']

                    for product_detail in ordered_product_details:
                        if available_qty <=0:
                            break

                        if available_qty > product_detail.available_qty:
                            product_detail.reserved_qty = product_detail.available_qty
                            available_qty = available_qty - product_detail.reserved_qty
                        else:
                            product_detail.reserved_qty = available_qty

                        product_detail.save()
                        order_product_reserved = OrderedProductReserved(product=product_detail.product, reserved_qty=available_qty)
                        order_product_reserved.order_product_reserved = product_detail
                        order_product_reserved.cart = cart
                        order_product_reserved.save()

                    cart_product.save()

                    serializer = CartSerializer(Cart.objects.get(id=cart.id))
                    msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                else:
                    msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                    return Response(msg, status=status.HTTP_200_OK)
            return Response(msg, status=status.HTTP_200_OK)

class CreateOrder(generics.ListAPIView):

    def post(self, request,*args, **kwargs):
        print(self.kwargs)
        cart_id = self.kwargs.get('cart_id')
        buyer_shop_id = self.request.POST.get('buyer_shop_id')
        billing_address_id = self.request.POST.get('billing_address_id')
        shipping_address_id = self.request.POST.get('shipping_address_id')
        msg = {'is_success': False, 'message': ['Cart is none'], 'response_data': None}
        #print(Cart.objects.filter(last_modified_by=self.request.user,id=cart_id).query)
        if Cart.objects.filter(last_modified_by=self.request.user,id=cart_id).exists():
            cart = Cart.objects.get(last_modified_by=self.request.user,id=cart_id)
            cart_products = CartProductMapping.objects.filter(cart=cart).values('cart_product', 'qty')

            if OrderedProductReserved.objects.filter(cart=cart).exists():
                for ordered_reserve in OrderedProductReserved.objects.filter(cart=cart):
                    ordered_reserve.order_product_reserved.available_qty = int(ordered_reserve.order_product_reserved.available_qty) - int(ordered_reserve.order_product_reserved.reserved_qty)
                    ordered_reserve.order_product_reserved.reserved_qty = 0
                    ordered_reserve.order_product_reserved.save()

                serializer = CartSerializer(Cart.objects.get(id=cart.id))
                # billing_address =
                order = Order(last_modified_by=request.user,ordered_cart=cart,order_no=cart.order_id)
                #order.billing_address = Address.objects.get(id=billing_address_id)
                #order.shipping_address = Address.objects.get(id=shipping_address_id)
                order.last_modified_by = self.request.user
                order.save()
                msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
            else:
                msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)

        return Response(msg, status=status.HTTP_200_OK)

#OrderedProductMapping.objects.filter()

class OrderList(generics.ListAPIView):
    serializer_class = OrderSerializer
    paginate_by = 10

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user)
        return queryset

class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user)
        return queryset

class DownloadInvoice(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """

    filename = 'invoice.pdf'
    template_name = 'admin/invoice/invoice.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))
        data = {"object": order_obj, }
        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response





