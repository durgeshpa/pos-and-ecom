from rest_framework import generics
from .serializers import (ProductsSearchSerializer,GramGRNProductsSearchSerializer,CartProductMappingSerializer,CartSerializer,
                          OrderSerializer, CustomerCareSerializer, OrderNumberSerializer)
from products.models import Product, ProductPrice, ProductOption,ProductImage
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
from datetime import datetime, timedelta
from django.utils import timezone

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
        #grn = GRNOrderProductMapping.objects.all()
        grn = OrderedProductMapping.objects.all()
        p_id_list = []
        for p in grn:
            product = p.product
            id = product.pk
            p_id_list.append(id)
        products = Product.objects.filter(pk__in=p_id_list)
        p_list = []
        msg = {'is_success': False, 'message': ['Sorry no product found!'], 'response_data': None}
        for product in products:
            id = product.pk
            name = product.product_name

            try:
                product_price = ProductPrice.objects.get(product=product)
            except ObjectDoesNotExist:
                msg['message'] = ['Product id %s  and name %s have price not found '%(product.id, product.product_name)]
                return Response(msg, status=400)

            try:
                product_option = ProductOption.objects.filter(product=product)[0]
            except ObjectDoesNotExist:
                msg['message'] = ['Product id %s  and name %s have product_option not found '%(product.id, product.product_name)]
                return Response(msg, status=400)

            try:
                product_image = ProductImage.objects.filter(product=product)
            except ObjectDoesNotExist:
                msg['message'] = ['Product id %s  and name %s have product_image not found '%(product.id, product.product_name)]
                return Response(msg, status=400)

            mrp = product_price.mrp
            ptr = product_price.price_to_retailer
            status = product_price.status

            pack_size = product_option.package_size.pack_size_name
            weight_value = product_option.weight.weight_value
            weight_unit = product_option.weight.weight_unit
            weight = product_option.weight.weight_name

            #image = product_image.image.url

            if name.startswith(request.data['product_name']):
                p_list.append({"name":name, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "weight":weight, "id":id,
                               "weight_value":weight_value,"weight_unit":weight_unit})
        if not p_list:
            return Response(msg,status=400)

        msg = {'is_success': True,
                'message': ['Products found'],
                'response_data':p_list }
        return Response(msg,
                        status=200)


class AddToCart(APIView):

    def post(self,request):
        cart_product = self.request.POST.get('cart_product')
        qty = self.request.POST.get('qty')
        shop_id = self.request.POST.get('shop_id')
        msg = {'is_success': False,'message': ['Sorry no any mapping with any shop!'],'response_data': None}

        if Shop.objects.filter(shop_owner=request.user).exists():

            if Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).exists():
                cart = Cart.objects.filter(last_modified_by=self.request.user, cart_status__in=['active', 'pending']).last()
                cart.cart_status = 'active'
                cart.save()
            else:
                cart = Cart(last_modified_by=self.request.user,cart_status='active')
                cart.save()

            # get Product
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
            msg = {'is_success': False, 'message': ['No any product available ins this cart'], 'response_data': None}

            for cart_product in cart_products:

                ordered_product_details = OrderedProductMapping.objects.filter(product=cart_product.cart_product).order_by('-expiry_date')
                ordered_product_sum = ordered_product_details.aggregate(available_qty_sum=Sum('available_qty'))

                if ordered_product_sum['available_qty_sum'] is not None:
                    #print("%s %s %s" %(int(ordered_product_sum['available_qty_sum']), int(cart_product.qty), str(cart_product.cart_product.id)))
                    if int(ordered_product_sum['available_qty_sum']) < int(cart_product.qty):
                        available_qty = int(ordered_product_sum['available_qty_sum'])
                        cart_product.qty_error_msg ='Available Quantity : %s'%(available_qty)
                        #cart_product.qty = available_qty

                    else:
                        available_qty = int(cart_product.qty)
                        cart_product.qty_error_msg = ''

                    # if int(available_qty) == 0:
                    #     cart_product.delete()
                    # else:
                    cart_product.save()

                    for product_detail in ordered_product_details:
                        if available_qty <=0:
                            break

                        product_detail.available_qty = 0 if available_qty > product_detail.available_qty else int(product_detail.available_qty) - int(available_qty)
                        product_detail.save()

                        order_product_reserved = OrderedProductReserved(product=product_detail.product,reserved_qty=available_qty)
                        order_product_reserved.order_product_reserved = product_detail
                        order_product_reserved.cart = cart
                        order_product_reserved.save()

                        available_qty = available_qty - int(product_detail.available_qty)

                    serializer = CartSerializer(cart)
                    msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                else:
                    msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                    return Response(msg, status=status.HTTP_200_OK)
            if CartProductMapping.objects.filter(cart=cart).count()<=0:
                msg = {'is_success': False, 'message': ['No any product available ins this cart'],'response_data': None}

        return Response(msg, status=status.HTTP_200_OK)

class CreateOrder(generics.ListAPIView):

    def post(self, request,*args, **kwargs):
        #print(self.kwargs)
        #cart_id = self.kwargs.get('cart_id')
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

        if Cart.objects.filter(last_modified_by=self.request.user,id=cart_id).exists():
            cart = Cart.objects.get(last_modified_by=self.request.user,id=cart_id)
            cart.cart_status = 'ordered_to_sp'
            cart.save()

            #cart_products = CartProductMapping.objects.filter(cart=cart).values('cart_product', 'qty')

            if OrderedProductReserved.objects.filter(cart=cart).exists():
                order = Order(last_modified_by=request.user,ordered_cart=cart,order_no=cart.order_id)

                try:
                    billing_address = Address.objects.get(id=billing_address_id)
                except ObjectDoesNotExist:
                    msg['message']=['Billing address not found']
                    return Response(msg, status=status.HTTP_200_OK)

                try:
                    shipping_address = Address.objects.get(id=shipping_address_id)
                except ObjectDoesNotExist:
                    msg['message']=['Shipping address not found']
                    return Response(msg, status=status.HTTP_200_OK)

                order.billing_address = billing_address
                order.shipping_address = shipping_address
                order.buyer_shop = shop

                order.total_mrp = float(total_mrp)
                order.total_tax_amount = float(total_tax_amount)
                order.total_final_amount = float(total_final_amount)

                order.order_status = 'ordered_to_sp'
                order.save()

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

#OrderedProductMapping.objects.filter()

class OrderList(APIView):
    paginate_by = 10
    #serializer_class = OrderSerializer

    def get(self,request,*args, **kwargs):
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
        try:
            queryset = Order.objects.filter(ordered_by=self.request.user)
            response_data = OrderSerializer(queryset,many=True)
            msg = {'is_success': True, 'message': [''], 'response_data': response_data}
            return Response(msg, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(msg, status=status.HTTP_200_OK)

    def get_queryset(self):
        queryset = Order.objects.filter(last_modified_by=self.request.user)
        return queryset
    #


class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self,*args,**kwargs):
        pk = self.kwargs.get('pk')
        queryset = Order.objects.filter(last_modified_by=self.request.user,id=pk)
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
