from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BannerSerializer, BannerPositionSerializer, BannerSlotSerializer, BannerDataSerializer
from banner.models import Banner, BannerPosition,BannerData
from rest_framework import viewsets
from rest_framework.decorators import list_route

class GetAllBannerListView(ListCreateAPIView):
    queryset = Banner.objects.filter(status=True)
    serializer_class = BannerSerializer

    @list_route
    def roots(self, request):
        queryset = BannerPosition.objects.filter(status=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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


class GetSlotBannerListView(APIView):

    # queryset = BannerData.objects.filter(slot__position_name=pos_name).order_by('banner_data_id')
    # serializer_class = BannerPositionSerializer

    def get(self,*args,**kwargs):
        pos_name = self.kwargs.get('slot_position_name')
        if pos_name:
            data = BannerData.objects.filter(slot__position_name=pos_name)
        else:
            data = BannerData.objects.all()
        is_success = True if data else False
        serializer = BannerDataSerializer(data,many=True)

        return Response({"message":"", "response_data": serializer.data ,"is_success": is_success})


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
