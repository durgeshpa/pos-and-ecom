from wms.models import Bin, Putaway, PutawayBinInventory
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

    def get(self, request):
        ids = self.request.GET.get('id')
        if ids:
            try:
                bins = Bin.objects.get(id=ids)
            except ObjectDoesNotExist:
                msg = {'is_success': False, 'message': ['Does Not Exist'], 'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                serializer = BinSerializer(bins)
                return Response({"bin": serializer.data})
        else:
            bins = Bin.objects.all()
            serializer = BinSerializer(bins, many=True)
            return Response({"bin": serializer.data})

    def post(self, request):
        warehouse = self.request.POST.get('warehouse')
        bin_id = self.request.POST.get('bin_id')
        bin_type = self.request.POST.get('bin_type')
        is_active = self.request.POST.get('is_active')
        sh = Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type == 'sp':
            bin_data = Bin.objects.create(warehouse=sh, bin_id=bin_id, bin_type=bin_type, is_active=is_active)
            serializer = (BinSerializer(bin_data))
            msg = {'is_success': True, 'message': ['Data added to bin'], 'response_data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)
        msg = ["Shop type must be sp"]
        return Response(msg, status=status.HTTP_200_OK)


class PutAwayViewSet(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        ids = self.request.GET.get('id')
        if ids:
            try:
                put_away = Putaway.objects.get(id=ids)
            except ObjectDoesNotExist:
                msg = {'is_success': False, 'message': ['Does Not Exist'], 'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                serializer = PutAwaySerializer(put_away)
                return Response({"put_away": serializer.data})
        else:
            put_away = Putaway.objects.all()
            serializer = PutAwaySerializer(put_away, many=True)
            return Response({"put_away": serializer.data})

    def post(self, request):
        msg = {'is_success': False, 'message': ['Some Required Field empty'], 'response_data': None}
        warehouse = self.request.POST.get('warehouse')
        if not warehouse:
            return Response(msg, status=status.HTTP_200_OK)
        put_away_quantity = self.request.POST.get('put_away_quantity')
        if not put_away_quantity:
            return Response(msg, status=status.HTTP_200_OK)
        batch_id = self.request.POST.get('batch_id')
        if not batch_id:
            return Response(msg, status=status.HTTP_200_OK)

        put_away = Putaway.objects.filter(batch_id=batch_id, warehouse=warehouse)
        if put_away.last().quantity < int(put_away_quantity):
            return Response({'is_success': False, 'message': ['Put_away_quantity should be equal to or'
                                                              ' less than quantity'], 'response_data': None},
                            status=status.HTTP_200_OK)

        sh = Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type == 'sp':
            put_away.update(putaway_quantity=put_away_quantity)

            serializer = (PutAwaySerializer(Putaway.objects.filter(batch_id=batch_id, warehouse=warehouse).last()))
        msg = {'is_success': True, 'message': ['quantity to be put away updated'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class PutAwayProduct(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """

        :param request:
        :return:
        """
        put_away = Putaway.objects.all()
        serializer = PutAwaySerializer(put_away, many=True, fields=('id', 'batch_id', 'sku', 'product_sku'))
        return Response({"put_away": serializer.data})


