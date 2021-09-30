import logging

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
from rest_framework import generics
from rest_framework import permissions, authentication
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from retailer_backend.utils import SmallOffsetPagination
from retailer_to_sp.models import (Order, CustomerCare, PickerDashboard)
from wms.services import check_whc_manager_coordinator_supervisor, check_whc_manager_coordinator_supervisor_picker
from .serializers import (CustomerCareSerializer, OrderNumberSerializer, PickerDashboardSerializer,
                          OrderSummarySerializers)
from ...common_function import get_response, validate_data_format, validate_id, serializer_error, \
    picker_dashboard_search, get_logged_user_wise_query_set_for_picker

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


class PickerDashboardCrudView(generics.GenericAPIView):
    """API view for PickerDashboard"""
    # authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = PickerDashboard.objects. \
        select_related('order', 'repackaging', 'shipment', 'picker_boy', 'zone', 'zone__warehouse',
                       'zone__warehouse__shop_owner', 'zone__warehouse__shop_type',
                       'zone__warehouse__shop_type__shop_sub_type', 'zone__supervisor', 'zone__coordinator',
                       'zone__warehouse', 'qc_area'). \
        prefetch_related('zone__putaway_users', 'zone__picker_users'). \
        order_by('-id')
    serializer_class = PickerDashboardSerializer

    def get(self, request):
        """ GET API for PickerDashboard """
        picker_dashboard_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get PickerDashboards for specific id """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            picker_dashboard_data = id_validation['data']

        else:
            """ GET PickerDashboard List """
            self.queryset = self.search_filter_picker_dashboard_data()
            picker_dashboard_total_count = self.queryset.count()
            picker_dashboard_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(picker_dashboard_data, many=True)
        msg = f"total count {picker_dashboard_total_count}" if picker_dashboard_data else "no picker_dashboard found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_coordinator_supervisor
    def put(self, request):
        """ Updates the given PickerDashboard"""
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update picker_dashboard', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        picker_dashboard_instance = id_validation['data'].last()
        serializer = self.serializer_class(instance=picker_dashboard_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("PickerDashboard Updated Successfully.")
            return get_response('PickerDashboard updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_picker_dashboard_data(self):
        """ Filters the PickerDashboard data based on request"""
        search_text = self.request.GET.get('search_text')
        warehouse = self.request.GET.get('warehouse')
        zone = self.request.GET.get('zone')
        qc_area = self.request.GET.get('qc_area')
        date = self.request.GET.get('date')
        picking_status = self.request.GET.get('picking_status')
        repackaging = self.request.GET.get('repackaging')
        order = self.request.GET.get('order')
        shipment = self.request.GET.get('shipment')
        picker_boy = self.request.GET.get('picker_boy')

        '''search using warehouse name, product's name'''
        if search_text:
            self.queryset = picker_dashboard_search(self.queryset, search_text)

        '''
            Filters using warehouse, product, zone, qc_area, date, picking_status, 
            repackaging, order, shipment, picker_boy
        '''
        if warehouse:
            self.queryset = self.queryset.filter(zone__warehouse__id=warehouse)

        if zone:
            self.queryset = self.queryset.filter(zone__id=zone)

        if qc_area:
            self.queryset = self.queryset.filter(qc_area__id=qc_area)

        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        if picking_status:
            self.queryset = self.queryset.filter(picking_status=picking_status)

        if repackaging:
            self.queryset = self.queryset.filter(repackaging__id=repackaging)

        if order:
            self.queryset = self.queryset.filter(order__id=order)

        if shipment:
            self.queryset = self.queryset.filter(shipment__id=shipment)

        if picker_boy:
            self.queryset = self.queryset.filter(picker_boy__id=picker_boy)

        return self.queryset.distinct('id')


class OrderSummaryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = PickerDashboard.objects.filter(
        picking_status__in=[PickerDashboard.PICKING_PENDING, PickerDashboard.PICKING_ASSIGNED,
                            PickerDashboard.PICKING_IN_PROGRESS, PickerDashboard.PICKING_COMPLETE,
                            PickerDashboard.MOVED_TO_QC]). \
        exclude(order__isnull=True). \
        order_by('order').values('order').annotate(status_list=ArrayAgg(F('picking_status')))
    serializer_class = OrderSummarySerializers

    @check_whc_manager_coordinator_supervisor_picker
    def get(self, request):
        """ GET API for PickerDashboards order summary """
        info_logger.info("PickerDashboard Order Summary GET api called.")
        """ GET PickerDashboard Order Summary List """
        self.queryset = get_logged_user_wise_query_set_for_picker(self.request.user, self.queryset)
        self.queryset = self.filter_zone_wise_summary_putaways_data()
        order_summary_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        order_wise_data = []
        for obj in order_summary_data:
            orders_dict = {"order": obj['order'], "status": ""}
            if PickerDashboard.PICKING_PENDING in obj['status_list'] or \
                    PickerDashboard.PICKING_ASSIGNED in obj['status_list'] or \
                    PickerDashboard.PICKING_IN_PROGRESS in obj['status_list']:
                orders_dict["status"] = "pending"
            elif PickerDashboard.PICKING_COMPLETE in obj['status_list']:
                orders_dict["status"] = "completed"
            elif PickerDashboard.MOVED_TO_QC in obj['status_list']:
                orders_dict["status"] = "moved_to_qc"
            order_wise_data.append(orders_dict)

        serializer = self.serializer_class(order_wise_data, many=True)
        msg = "" if order_wise_data else "no order found"
        return get_response(msg, serializer.data, True)

    def filter_zone_wise_summary_putaways_data(self):
        order = self.request.GET.get('order')
        date = self.request.GET.get('date')

        '''Filters using order, date '''
        if order:
            self.queryset = self.queryset.filter(order=order)

        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        return self.queryset
