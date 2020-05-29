from wms.models import Bin, Putaway
from rest_framework import viewsets
from .serializers import BinSerializer, PutAwaySerializer
from rest_framework.response import Response
from rest_framework import status
from shops.models import Shop
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist


class BinViewSet(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        warehouse = self.request.POST.get('warehouse')
        bin_id = self.request.POST.get('bin_id')
        bin_type = self.request.POST.get('bin_type')
        is_active = self.request.POST.get('is_active')
        sh =Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type=='sp':
            bo = Bin.objects.create(warehouse=sh, bin_id=bin_id, bin_type=bin_type, is_active=is_active)
            serializer = (BinSerializer(bo))
            msg = {'is_success': True, 'message': ['Data added to bin'], 'response_data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)
        msg = ["Shop type must be sp"]
        return Response(msg, status=status.HTTP_200_OK)


class PutAwayViewSet(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        putaway = Putaway.objects.all()
        serializer = PutAwaySerializer(putaway, many=True)
        return Response({"putaway": serializer.data})

    def get(self, request):
        id = self.request.GET.get('id')
        try:
            putaway = Putaway.objects.get(id=id)
        except ObjectDoesNotExist:
            msg = {'is_success':False, 'message':['Does Not Exist'], 'response_data':None}
            return Response(msg, status=status.HTTP_200_OK)
        else:
            serializer = PutAwaySerializer(putaway)
            return Response({"putaway": serializer.data})

    def post(self, request):
        warehouse = self.request.POST.get('warehouse')
        putaway_quantity = self.request.POST.get('putaway_quantity')
        batch_id = self.request.POST.get('batch_id')
        putA = Putaway.objects.filter(batch_id=batch_id, warehouse=warehouse)
        msg = {'is_success': False, 'message': ['Putaway_quantity should be equal to or less than quantity'], 'response_data': None}
        if putA.last().quantity < int(putaway_quantity):
            return Response(msg, status=status.HTTP_200_OK)

        sh = Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type=='sp':
            putA.update(putaway_quantity=putaway_quantity)

            serializer = (PutAwaySerializer(Putaway.objects.filter(batch_id=batch_id, warehouse=warehouse).last()))
        msg = {'is_success': True, 'message': ['quantity to be put away updated'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)