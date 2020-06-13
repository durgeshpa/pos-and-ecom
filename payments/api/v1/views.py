import requests
import datetime
import traceback
import sys
import logging
import json
import re

from django.shortcuts import render
from django.shortcuts import redirect

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
from rest_framework import serializers

from django.db import transaction
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from common.data_wrapper_view import DataWrapperViewSet

from .serializers import ShipmentPaymentSerializer, ReadShipmentPaymentSerializer, \
    ShipmentPaymentSerializer2, OrderPaymentSerializer, PaymentImageSerializer
from accounts.models import UserWithName
from retailer_to_sp.models import OrderedProduct, OrderedProductMapping
from payments.models import ShipmentPayment, PaymentMode, \
    Payment, OrderPayment, PaymentImage

from retailer_to_sp.views import update_shipment_status_with_id
from retailer_to_sp.api.v1.views import update_trip_status    

from sp_to_gram.models import create_credit_note

from common.common_utils import convert_hash_using_hmac_sha256
from common.data_wrapper import format_serializer_errors

BHARATPE_BASE_URL = "http://api.bharatpe.io:8080"
BHARATPE_PRODUCTION_BASE_URL = "https://api.bharatpe.in"

logger = logging.getLogger(__name__)

# ask front end to send request to shipment-payment/ order payment api if it succeeds
class SendCreditRequestAPI(APIView):
    # authentication_classes = (authentication.TokenAuthentication,)
    # permission_classes = (permissions.IsAuthenticated,)
    permission_classes = (AllowAny,)
    def post(self, request):
        context = {}
        try:
            headers = {'Content-Type': 'application/json', 
                        'Accept':'application/json',
                        'hash': convert_hash_using_hmac_sha256(request.data)}
            resp = requests.post(BHARATPE_BASE_URL+"/create_invoice/", data = json.dumps(request.POST), headers=headers)        
            data = json.loads(resp.content)         
            msg = {'is_success': True,
                   'message': [],
                   'response_data':data }

            #if it fails then also create some entry: 
            #return redirect('/payments/api/v1/shipment-payment/')

            return Response(msg,
                             status=200)
        except Exception as e:
            logging.info("Class name: %s - Error = %s:"%('SendCreditRequestAPI',str(e)))
            logging.info(traceback.format_exc(sys.exc_info()))
            msg = {'is_success': False,
                   'message': [],
                   'response_data':str(e)}
            # if it fails add entry with not success and generate payment id for future reference
            return Response(msg,
                             status=400)


class CreditOTPResponseAPI(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        context = {}
        try:
            headers = {'Content-Type': 'application/json', 
                        'Accept':'application/json',
                        'hash': convert_hash_using_hmac_sha256(payload)}
            resp = requests.post(BHARATPE_BASE_URL+"/otp-response", data = json.dumps(request.POST), headers=headers)        
            data = json.loads(resp.content)         
            return (True, "payment successful")
            msg = {'is_success': True,
                   'message': [],
                   'response_data':data }
            return Response(msg,
                             status=200)
        except Exception as e:
            logging.info("Class name: %s - Error = %s:"%('CreditOTPResponseAPI',str(e)))
            logging.info(traceback.format_exc(sys.exc_info()))
            msg = {'is_success': False,
                   'message': [],
                   'response_data':str(e)}
            return Response(msg,
                             status=400)


class BharatpeCallbackAPI(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)           

    # receive delayed response from bharatpe
    def post(self, request):
        try:
            payment_id = request.POST['payment_id']
            payment_status = request.POST['payment_status']
            payment = Payment.objects.filter(payment_id=payment_id)
            if payment.exists():
                payment[0].is_payment_approved = payment_status
                payment[0].save()
        except Exception as e:
            logging.info("Class name: %s - Error = %s:"%('Bharatpe callback',str(e)))
            logging.info(traceback.format_exc(sys.exc_info()))
            print (str(e))



# set payment_received = True fetch by payment_id 
def callback_url(self, request):
    try:
        payment_id = request.POST['payment_id']
        payment_status = request.POST['payment_status']
        payment = Payment.objects.filter(payment_id=payment_id)
        if payment.exists():
            payment[0].is_payment_approved = payment_status
            payment[0].save()
    except Exception as e:
        logging.info("Class name: %s - Error = %s:"%('Bharatpe callback',str(e)))
        logging.info(traceback.format_exc(sys.exc_info()))
        print (str(e))
        

def format_serializer_error(e):
    errors = []
    for field in e: #serializer.errors:
        for error in e[field]:#serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field,error))
            errors.append(result)
    return errors


class CustomError(Exception):
    pass


from rest_framework.exceptions import APIException

# class ShipmentPaymentView(DataWrapperViewSet):
class ShipmentPaymentView(viewsets.ModelViewSet):
    '''
    This class handles all operation of ordered product mapping
    '''
    model = ShipmentPayment
    serializer_class = ShipmentPaymentSerializer
    queryset = ShipmentPayment.objects.all()
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': ReadShipmentPaymentSerializer,
            'list': ReadShipmentPaymentSerializer,
            'create': ShipmentPaymentSerializer,
            'update': ShipmentPaymentSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def errors_response(self, serializer_errors):
        errors = []
        for field in serializer_errors:
            for error in serializer_errors[field]:
                if 'non_field_errors' in field:
                    result = error
                    errors.append(result)
                elif field in ['payment_data', 'user_documents']:
                    error_msg = ''
                    if error:
                        if isinstance(error, dict):
                            for e in error:
                                error_msg = error_msg.join(error[e])
                            errors.append(error_msg)
                        else:
                            errors.append(error)
                else:
                    errors.append(error)
        return errors

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            msg = {'is_success': True,
                   'message': ["Payment created successfully"],
                   'response_data': serializer.data,
                   'is_pan_required': serializer.context.get('is_pan_required', False)}
            return Response(msg, status=status.HTTP_200_OK)

        else:
            msg = {'is_success': False,
                   'message': [i for i in self.errors_response(serializer.errors)],
                   'response_data': None,
                   'is_pan_required': serializer.context.get('is_pan_required', False)}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)


# class OrderPaymentView(DataWrapperViewSet):
class OrderPaymentView(viewsets.ModelViewSet):
    '''
    This class handles all operation of ordered product mapping
    '''
    # permission_classes = (AllowAny,)
    model = OrderPayment
    serializer_class = OrderPaymentSerializer
    queryset = OrderPayment.objects.all()
    parser_classes = (FormParser, MultiPartParser)
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = OrderPaymentFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': OrderPaymentSerializer1,
            'list':OrderPaymentSerializer1,
            'create':OrderPaymentSerializer,
            'update':OrderPaymentSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        try:
            order = request.data.get('order', None)
            paid_by = request.data.get('paid_by', None)
            if not Order.objects.filter(pk=order).exists():
                msg = {'is_success': False,
                                'message': "Order not found",
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

            order = request.data.get('order', None)
            order = Order.objects.get(pk=order)

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
                        payment.reference_no = reference_no
                        payment.online_payment_type = online_payment_type
                    payment.save()

                    # create order payment
                    order_payment = OrderPayment.objects.create(
                        paid_amount = paid_amount,
                        parent_payment = payment,
                        order = order
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


class PaymentImageUploadView(ListCreateAPIView, RetrieveUpdateDestroyAPIView):
    serializer_class = PaymentImageSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)
    lookup_field = 'pk'

    def get_queryset(self):
        queryset = PaymentImage.objects.filter(user=self.request.user)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # payment_image, created = PaymentImage.objects.update_or_create(
            #     reference_image=request.data['reference_image'],
            #     defaults={'user': self.request.user, 'reference_number':reference_number})
            
            serializer.save(user=self.request.user)
            msg = {'is_success': True,
                    'message': ["Image uploaded successfully!"],
                    'response_data': {'payment_image_id':serializer.data['id']}}
            return Response(msg,
                            status=status.HTTP_200_OK)
        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': ["%s objects found" % (queryset.count())],
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        
      # return self.destroy(request, *args, **kwargs)

        try:            
            image = PaymentImage.objects.filter(pk=kwargs['pk'])
            if image.exists():
                image.delete()
                text = "Image deleted successfully!"
            else:
                text = "Image not found"
            msg = {'is_success': True,
                    'message': [text],
                    'response_data': None}
            return Response(msg,
                            status=status.HTTP_200_OK)

        except Exception as e:
            msg = {'is_success': False,
                'message': [str(e)],
                'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)
