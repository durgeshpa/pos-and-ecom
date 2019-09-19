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
import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from common.data_wrapper_view import DataWrapperViewSet

from .serializers import ShipmentPaymentSerializer, CashPaymentSerializer, \
    ShipmentPaymentSerializer1 
from payments.models import ShipmentPayment, CashPayment


# class ShipmentPaymentView(DataWrapperViewSet):
class ShipmentPaymentView(viewsets.ModelViewSet):
    '''
    This class handles all operation of ordered product mapping
    '''
    permission_classes = (AllowAny,)
    model = ShipmentPayment
    serializer_class = ShipmentPaymentSerializer
    queryset = ShipmentPayment.objects.all()
    # authentication_classes = (authentication.TokenAuthentication,)
    # permission_classes = (permissions.IsAuthenticated,)
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
        # import pdb; pdb.set_trace()
        #serializer = ShipmentPaymentSerializer(data=request.data, many=True)
        serializer = self.get_serializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save() #user=self.request.user
            msg = {'is_success': True,
                    'message': ["Payment created successfully"],
                    'response_data': None}
            return Response(msg,
                            status=status.HTTP_200_OK)
        else:
            # errors = []
            # for field in serializer.errors:
            #     for error in serializer.errors[field]:
            #         if 'non_field_errors' in field:
            #             result = error
            #         else:
            #             result = ''.join('{} : {}'.format(field,error))
            #         errors.append(result)
            msg = {'is_success': False,
                    'message': serializer.errors, #[error for error in errors],
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