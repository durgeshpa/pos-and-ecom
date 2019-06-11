from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BannerSerializer, BannerPositionSerializer, BannerSlotSerializer, BannerDataSerializer, BrandSerializer
from banner.models import Banner, BannerPosition,BannerData, BannerSlot,Page
from rest_framework import viewsets
from rest_framework.decorators import list_route
import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from shops.models import Shop, ParentRetailerMapping

from retailer_to_sp.models import OrderedProduct, Feedback

class GetSlotBannerListView(APIView):

    # queryset = BannerData.objects.filter(slot__position_name=pos_name).order_by('banner_data_id')
    # serializer_class = BannerPositionSerializer
    permission_classes = (AllowAny,)
    def get(self,*args,**kwargs):

        startdate = datetime.datetime.now()
        position_name= self.kwargs.get('page_name')
        pos_name = self.kwargs.get('banner_slot')
        shop_id = self.request.GET.get('shop_id')
        shipment_id, can_write_feedback = '', False

        if pos_name and position_name and shop_id and shop_id != '-1':

            if Shop.objects.get(id=shop_id).retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
                data = BannerData.objects.filter(banner_data__status=True, slot__page__name=position_name,slot__bannerslot__name=pos_name, slot__shop=parent.id).filter(Q(banner_data__banner_start_date__isnull=True) | Q(banner_data__banner_start_date__lte=startdate, banner_data__banner_end_date__gte=startdate))
                is_success = True if data else False
                message = "" if is_success else "Banners are currently not available"
                serializer = BannerDataSerializer(data,many=True)

                '''
                Can Fill Feedback Code Start
                '''
                order_product = OrderedProduct.objects.filter(order__buyer_shop__shop_owner=Shop.objects.get(id=shop_id).shop_owner).order_by('created_at')
                if order_product.exists() and (not hasattr(order_product, 'shipment_feedback')):
                    shipment_id = order_product.last().id
                    can_write_feedback = True
            else:
                data = BannerData.objects.filter(banner_data__status=True, slot__page__name=position_name,slot__bannerslot__name=pos_name,slot__shop=None ).filter(Q(banner_data__banner_start_date__isnull=True) | Q(banner_data__banner_start_date__lte=startdate, banner_data__banner_end_date__gte=startdate))
                is_success = True if data else False
                message = "" if is_success else "Banners are currently not available"
                serializer = BannerDataSerializer(data,many=True)

            return Response({"message":[message], "response_data": serializer.data ,"is_success": is_success,"shipment_id": shipment_id, "can_write_feedback": can_write_feedback})

        else:
            data = BannerData.objects.filter(banner_data__status=True, slot__page__name=position_name,slot__bannerslot__name=pos_name, slot__shop=None).filter(Q(banner_data__banner_start_date__isnull=True) | Q(banner_data__banner_start_date__lte=startdate, banner_data__banner_end_date__gte=startdate))
            is_success = True if data else False
            message = "" if is_success else "Banners are currently not available"
            serializer = BannerDataSerializer(data,many=True)

            return Response({"message":[message], "response_data": serializer.data ,"is_success": is_success,"shipment_id": shipment_id, "can_write_feedback": can_write_feedback})


'''class GetAllBannerListView(ListCreateAPIView):
    startdate = datetime.datetime.now()
    queryset = Banner.objects.filter(status= True, banner_start_date__lte= startdate, banner_end_date__gte= startdate)
    serializer_class = BannerSerializer
    @list_route
    def roots(self, request):
        queryset = BannerPosition.objects.filter(status=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
'''

'''class GetSlotBannerListView(ListCreateAPIView):
    queryset = BannerData.objects.all().order_by('banner_data_order')
    serializer_class = BannerDataSerializer
    @list_route
    def roots(self, request):
        queryset = BannerData.objects.all().order_by('banner_data_order')
        serializer = self.get_serializer(queryset, many=True)
        is_success = True if queryset else False
        return Response({"message":"", "response_data": serializer.data ,"is_success": is_success})
       '''



class GetPageBannerListView(APIView):

    # queryset = BannerData.objects.filter(slot__position_name=pos_name).order_by('banner_data_id')
    # serializer_class = BannerPositionSerializer
    permission_classes = (AllowAny,)
    def get(self,*args,**kwargs):
        startdate = datetime.datetime.now()
        pos_name = self.kwargs.get('page_name')
        if pos_name:
            data = BannerData.objects.filter(banner_data__status=True, slot__page__name=pos_name, banner_data__banner_start_date__lte=startdate, banner_data__banner_end_date__gte=startdate )
        else:
            data = BannerData.objects.filter(banner_data__status=True, banner_data__banner_start_date__lte=startdate, banner_data__banner_end_date__gte=startdate)
        is_success = True if data else False
        banner_data_serializer = BannerDataSerializer(data,many=True)

        return Response({"message":[""], "response_data": banner_data_serializer.data ,"is_success": is_success})


'''@api_view(['GET', 'POST'])
def all_slot_list_view(request):
    """
    Retrieve, update or delete a code banner.
    """
    if request.method == 'GET':
        slots = BannerPosition.objects.all()
        serializer = BannerSlotSerializer(slots, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = BannerSlotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET', 'PUT', 'DELETE'])
def slot_detail_view(request,pk):
    """
    Retrieve, update or delete a code banner.
    """
    try:
        position = BannerPosition.objects.get(pk=pk)
    except Banner.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = BannerSlotSerializer(position)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = BannerSlotSerializer(position, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        banner.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
       '''
