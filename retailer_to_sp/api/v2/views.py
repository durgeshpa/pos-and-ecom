import logging
import requests
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.db.models import Count, F
from rest_framework import permissions
from rest_auth import authentication
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from common.common_utils import create_file_name, create_merge_pdf_name, merge_pdf_files
from common.constants import PREFIX_RETURN_CHALLAN_FILE_NAME, CHALLAN_DOWNLOAD_ZIP_NAME
from retailer_to_sp.models import (Order, CustomerCare, Return, ReturnOrder)
from addresses.models import ShopRoute
from wms.common_functions import get_response
from .serializers import (CustomerCareSerializer, OrderNumberSerializer,
                          GFReturnOrderProductSerializer, ReturnChallanSerializer)

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
from retailer_to_sp.api.v1.views import return_challan_generation


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
    
    def get(self, request, pk=None):
        if pk:
            try:
                return_order = ReturnOrder.objects.get(id=pk)
                serializer = GFReturnOrderProductSerializer(return_order)
                msg = "return order" if return_order else "no return orders found"
                return get_response(msg, serializer.data, True)
            except ReturnOrder.DoesNotExist:
                return get_response("Return Order does not exists", None, False)
        else:
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
            serializer = GFReturnOrderProductSerializer(returns, many=True)
            msg = "return orders" if returns else "no return orders found"
            return get_response(msg, serializer.data, True)
        

class GetReturnChallan(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request, *args, **kwargs):
        try:
            route = self.request.GET.get('route')

            shop_qs = ShopRoute.objects.filter(route_id=route).values_list('shop_id', flat=True)

            return_orders = ReturnOrder.objects.filter(buyer_shop__id__in=shop_qs,
                                                      return_type=ReturnOrder.SUPERSTORE_WAREHOUSE,
                                                      return_status='RETURN_REQUESTED')

            # return_order = ReturnOrder.objects.get(id=kwargs['pk'])
            file_path_list = []
            pdf_created_date = []
            for return_order in return_orders:
                try:
                    if return_order.return_invoice and return_order.return_invoice.invoice_pdf and return_order.return_invoice.invoice_pdf.url:
                        pass
                    else:
                        return_order = return_challan_generation(request, return_order.id)
                except:
                    return_order = return_challan_generation(request, return_order.id)
                file_path_list.append(return_order.return_invoice.invoice_pdf.url)
                pdf_created_date.append(return_order.created_at)

            prefix_file_name = CHALLAN_DOWNLOAD_ZIP_NAME
            merge_pdf_name = create_merge_pdf_name(prefix_file_name, pdf_created_date)
            merged_file_url = merge_pdf_files(file_path_list, merge_pdf_name)
            file_pointer = requests.get(merged_file_url)
            response = HttpResponse(file_pointer.content, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(merge_pdf_name)
            return response
        except ReturnOrder.DoesNotExist:
            return get_response("Return Order does not exists", None, False)


class ReturnChallanList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        try:
            """
                Return the list of return challan grouped on the basis of shop routes
            """

            return_order_qs = ReturnOrder.objects.filter(
                return_type=ReturnOrder.SUPERSTORE_WAREHOUSE, return_status='RETURN_REQUESTED')

            # Filter queryset
            return_order_qs = self.search_filter_return_data(return_order_qs)

            # group by shop routes
            return_order_qs = return_order_qs.values('buyer_shop__shop_routes').annotate(
                no_of_challan=Count('buyer_shop__shop_routes'), warehouse=F('seller_shop'))

            serializer = ReturnChallanSerializer(return_order_qs, many=True)
            msg = "Return Challan List"
            return get_response(msg, serializer.data, True)
        except Exception as e:
            info_logger.info(e)
            return e

    def search_filter_return_data(self, return_order_qs):
        city = self.request.GET.get('city')
        route = self.request.GET.get('route')
        date = datetime.strptime(self.request.GET.get('created_at', datetime.now().date().isoformat()), "%Y-%m-%d")
        date = date + timedelta(days=1)

        if route:
            return_order_qs = return_order_qs.filter(buyer_shop__shop_routes__route_id=route)

        if city:
            return_order_qs = return_order_qs.filter(buyer_shop__shop_routes__route__city_id=city)

        if date:
            return_order_qs = return_order_qs.filter(created_at__lte=date)

        return return_order_qs