import logging

from rest_framework import permissions
from rest_auth import authentication
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from retailer_to_sp.models import (Order, CustomerCare, Return, ReturnOrder)
from wms.common_functions import get_response
from .serializers import (CustomerCareSerializer, OrderNumberSerializer, 
                          GFReturnOrderProductSerializer)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


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


class GFReturnOrderList(APIView):
    
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request):
        returns = ReturnOrder.objects.filter(return_type=ReturnOrder.SUPERSTORE_WAREHOUSE)
        search_text = request.query_params.get('search_text')
        if search_text:
            returns = returns.filter(return_order_products__product__product_name__icontains=search_text).distinct('id')
        return_status = request.query_params.get('return_status')
        if return_status:
            returns = returns.filter(return_status=return_status)
        seller_shop = request.query_params.get('seller_shop')
        if seller_shop:
            returns = returns.filter(seller_shop=seller_shop)
        buyer_shop = request.query_params.get('buyer_shop')
        if buyer_shop:
            returns = returns.filter(buyer_shop=buyer_shop)
        return_no = request.query_params.get('return_no')
        if return_no:
            returns = returns.filter(return_no=return_no)
        serializer =  GFReturnOrderProductSerializer(returns, many=True)
        msg = "return orders" if returns else "no return orders found"
        return get_response(msg, serializer.data, True)
        
        