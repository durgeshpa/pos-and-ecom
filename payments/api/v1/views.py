from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework import permissions, authentication
from rest_framework.decorators import list_route
from rest_framework.parsers import FormParser, MultiPartParser

import datetime

from django.db import transaction
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from common.data_wrapper_view import DataWrapperViewSet

from .serializers import ShipmentPaymentSerializer, CashPaymentSerializer, \
    ShipmentPaymentSerializer1, ShipmentPaymentSerializer2
from accounts.models import UserWithName
from retailer_to_sp.models import OrderedProduct
from payments.models import ShipmentPayment, CashPayment, OnlinePayment, PaymentMode, \
    Payment, OrderPayment



# class ShipmentPaymentView(DataWrapperViewSet):
class ShipmentPaymentView(viewsets.ModelViewSet):
    '''
    This class handles all operation of ordered product mapping
    '''
    #permission_classes = (AllowAny,)
    model = ShipmentPayment
    serializer_class = ShipmentPaymentSerializer
    queryset = ShipmentPayment.objects.all()
    parser_classes = (FormParser, MultiPartParser)
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = ShipmentPaymentFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': ShipmentPaymentSerializer1,
            'list':ShipmentPaymentSerializer1,
            'create':ShipmentPaymentSerializer,
            'update':ShipmentPaymentSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        #import pdb; pdb.set_trace()
        try:
            shipment = request.data.get('shipment', None)
            paid_by = request.data.get('paid_by', None)
            if not OrderedProduct.objects.filter(pk=shipment).exists():
                msg = {'is_success': False,
                                'message': "Shipment not found",
                                'response_data': None }
                return Response(msg,
                                status=status.HTTP_406_NOT_ACCEPTABLE)

            if not UserWithName.objects.filter(phone_number=paid_by).exists():
                msg = {'is_success': False,
                                'message': "Paid by user not found",
                                'response_data': None }
                return Response(msg,
                                status=status.HTTP_406_NOT_ACCEPTABLE)

            serializer = self.get_serializer(data=request.data.get('payment_data'), many=True)
            if not serializer.is_valid():
                msg = {'is_success': False,
                    'message': serializer.errors,
                    'response_data': None }
                return Response(msg,
                                status=status.HTTP_406_NOT_ACCEPTABLE)

            shipment = request.data.get('shipment', None)
            shipment = OrderedProduct.objects.get(pk=shipment)

            paid_by = request.data.get('paid_by', None)
            paid_by = UserWithName.objects.get(phone_number=paid_by)

            with transaction.atomic():
                for item in request.data.get('payment_data'):
                    # serializer = self.get_serializer(data=item)
                    # if serializer.is_valid():
                    paid_amount = item.get('paid_amount', None)
                    payment_mode_name = item.get('payment_mode_name', None)
                    payment_screenshot = item.get('payment_screenshot', None)
                    reference_no = item.get('reference_no', None)
                    online_payment_type = item.get('online_payment_type', None)
                    description = item.get('description', None)

                    # create payment
                    payment = Payment.objects.create(
                        paid_amount = paid_amount,
                        payment_mode_name = payment_mode_name,
                        paid_by = paid_by,
                        payment_screenshot = payment_screenshot,
                        )
                    if payment_mode_name == "online_payment":
                        # if reference_no is None:
                        #     raise serializers.ValidationError("Reference number is required!")
                        #     # raise ValidationError("Reference number is required") 
                        # if online_payment_type is None:
                        #     raise serializers.ValidationError("Online payment type is required!")

                        payment.reference_no = reference_no
                        payment.online_payment_type = online_payment_type
                    payment.save()

                    # create order payment
                    order_payment = OrderPayment.objects.create(
                        paid_amount = paid_amount,
                        parent_payment = payment,
                        order = shipment.order
                        )
                    
                    # create shipment payment
                    shipment_payment = ShipmentPayment.objects.create(
                        paid_amount = paid_amount,
                        parent_order_payment = order_payment,
                        shipment = shipment
                        )

                msg = {'is_success': True,
                        'message': ["Payment created successfully"],
                        'response_data': None}
                return Response(msg,
                        status=status.HTTP_200_OK)

        except Exception as e:
            # msg = {'is_success': False,
            #         'message': str(e), #[error for error in errors],
            #         'response_data': None }
            errors = []
            for field in e: #serializer.errors:
                for error in e[field]:#serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': errors, #[error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)


class CashPaymentView(DataWrapperViewSet):
    '''
    This class handles all operation of ordered product mapping
    '''
    #permission_classes = (AllowAny,)
    model = CashPayment
    serializer_class = CashPaymentSerializer
    queryset = CashPayment.objects.all()
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = CashPaymentFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': CashPaymentSerializer,
            'list':CashPaymentSerializer,
            'create':CashPaymentSerializer,
            'update':CashPaymentSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class        