import logging
from django.http import JsonResponse
import requests
import json
import sys
import traceback

from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters import rest_framework as filters
from django.core.cache import cache
from django.conf import settings

from .data_wrapper import data_wrapper_response,  format_data


'''
This class is to manipulate data before returning data
Extend this class to use its functionalities
'''
class DataWrapperViewSet(viewsets.ModelViewSet):
    # renderer_classes =(CustomBrowsableAPIRenderer,)

    def dispatch(self, *args, **kwargs):
        result =  super(DataWrapperViewSet, self).dispatch(*args, **kwargs)
        data = format_data(result)
        return data

class DataWrapperListRetrieveViewSet(mixins.ListModelMixin, 
                                     mixins.RetrieveModelMixin, 
                                     viewsets.GenericViewSet):
    def dispatch(self, *args, **kwargs):
        result =  super(DataWrapperListRetrieveViewSet, self).dispatch(*args, **kwargs)
        data = format_data(result)
        return data

class DataWrapperCreateUpdateViewSet(mixins.CreateModelMixin, 
                                     mixins.UpdateModelMixin, 
                                     viewsets.GenericViewSet):
    def dispatch(self, *args, **kwargs):
        result =  super(DataWrapperCreateUpdateViewSet, self).dispatch(*args, **kwargs)
        data = format_data(result)
        return data

'''
This class is to manipulate data for generic api views 
Extend this class to use its functionalities
'''
class GenericDataWrapper(object):

    def dispatch(self, *args, **kwargs):
        result =  super(GenericDataWrapper, self).dispatch(*args, **kwargs)
        data = format_data(result)      
        return data


class DataWrapperView(APIView):
    def dispatch(self, *args, **kwargs):
        result =  super(GenericDataWrapper, self).dispatch(*args, **kwargs)
        data = format_data(result)      
        return data