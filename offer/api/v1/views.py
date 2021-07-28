from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import GenericAPIView, CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import OfferBannerSerializer, OfferBannerPositionSerializer, OfferBannerSlotSerializer, \
    OfferBannerDataSerializer, BrandSerializer, TopSKUSerializer, OfferPageSerializers, OfferBannerSlotSerializers
from offer.models import OfferBanner, OfferBannerPosition, OfferBannerData, OfferBannerSlot, OfferPage, TopSKU
from retailer_to_sp.models import OrderedProduct, Feedback
from rest_framework import viewsets
from rest_framework.decorators import list_route
import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from shops.models import Shop, ParentRetailerMapping

import logging
import datetime

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from retailer_backend.utils import SmallOffsetPagination

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format
from offer.services import offer_page_search

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class GetSlotOfferBannerListView(APIView):
    # queryset = BannerData.objects.filter(slot__position_name=pos_name).order_by('banner_data_id')
    # serializer_class = BannerPositionSerializer
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):

        startdate = datetime.datetime.now()
        position_name = self.kwargs.get('page_name')
        pos_name = self.kwargs.get('banner_slot')
        shop_id = self.request.GET.get('shop_id')

        if pos_name and position_name and shop_id and shop_id != '-1':
            if Shop.objects.get(id=shop_id).retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
                data = OfferBannerData.objects.filter(offer_banner_data__status=True, slot__page__name=position_name,
                                                      slot__offerbannerslot__name=pos_name,
                                                      slot__shop=parent.id).filter(
                    Q(offer_banner_data__offer_banner_start_date__isnull=True) | Q(
                        offer_banner_data__offer_banner_start_date__lte=startdate,
                        offer_banner_data__offer_banner_end_date__gte=startdate))
                is_success = True if data else False
                message = "" if is_success else "Banners are currently not available"
                serializer = OfferBannerDataSerializer(data, many=True)
            else:
                data = OfferBannerData.objects.filter(offer_banner_data__status=True, slot__page__name=position_name,
                                                      slot__offerbannerslot__name=pos_name, slot__shop=None).filter(
                    Q(offer_banner_data__offer_banner_start_date__isnull=True) | Q(
                        offer_banner_data__offer_banner_start_date__lte=startdate,
                        offer_banner_data__offer_banner_end_date__gte=startdate))
                is_success = True if data else False
                message = "" if is_success else "Banners are currently not available"
                serializer = OfferBannerDataSerializer(data, many=True)

            return Response({"message": [message], "response_data": serializer.data, "is_success": is_success})

        else:
            data = OfferBannerData.objects.filter(offer_banner_data__status=True, slot__page__name=position_name,
                                                  slot__offerbannerslot__name=pos_name, slot__shop=None).filter(
                Q(offer_banner_data__offer_banner_start_date__isnull=True) | Q(
                    offer_banner_data__offer_banner_start_date__lte=startdate,
                    offer_banner_data__offer_banner_end_date__gte=startdate))
            is_success = True if data else False
            message = "" if is_success else "Banners are currently not available"
            serializer = OfferBannerDataSerializer(data, many=True)
            return Response({"message": [message], "response_data": serializer.data, "is_success": is_success})


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

    def get(self, *args, **kwargs):
        startdate = datetime.datetime.now()
        pos_name = self.kwargs.get('page_name')
        if pos_name:
            data = BannerData.objects.filter(banner_data__status=True, slot__page__name=pos_name,
                                             banner_data__banner_start_date__lte=startdate,
                                             banner_data__banner_end_date__gte=startdate)
        else:
            data = BannerData.objects.filter(banner_data__status=True, banner_data__banner_start_date__lte=startdate,
                                             banner_data__banner_end_date__gte=startdate)
        is_success = True if data else False
        banner_data_serializer = BannerDataSerializer(data, many=True)

        return Response({"message": [""], "response_data": banner_data_serializer.data, "is_success": is_success})


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


class GetTopSKUListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):

        startdate = datetime.datetime.now()
        shop_id = self.request.GET.get('shop_id')
        date = datetime.datetime.now()

        if shop_id and shop_id != '-1':
            if Shop.objects.get(id=shop_id).retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
                data = TopSKU.objects.filter(start_date__lte=date, end_date__gte=date, status=True, shop=parent.id)
                is_success = True if data else False
                message = "Top SKUs" if is_success else "No Top SKUs"
                serializer = TopSKUSerializer(data, many=True)
            else:
                data = TopSKU.objects.filter(start_date__lte=date, end_date__gte=date, status=True, shop=None)
                is_success = True if data else False
                message = "" if is_success else "No Top SKUs"
                serializer = TopSKUSerializer(data, many=True)

            return Response({"message": [message], "response_data": serializer.data, "is_success": is_success})

        else:
            data = TopSKU.objects.filter(start_date__lte=date, end_date__gte=date, status=True, shop=None)
            is_success = True if data else False
            message = "" if is_success else "No Top SKUs"
            serializer = TopSKUSerializer(data, many=True)
            return Response({"message": [message], "response_data": serializer.data, "is_success": is_success})


class OfferPageView(GenericAPIView):
    """
        Get OfferPage
        Add OfferPage
        Search OfferPage
        List OfferPage
        Update OfferPage
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = OfferPage.objects.values('id', 'name',).order_by('-id')
    serializer_class = OfferPageSerializers

    def get(self, request):
        """ GET API for Offer Page """

        info_logger.info("Offer PageGET api called.")
        offer_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Offer Page for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            offer_page = id_validation['data']
        else:
            """ GET Offer Page List """
            self.queryset = self.offer_page_search()
            offer_total_count = self.queryset.count()
            offer_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_page, many=True)
        msg = f"total count {offer_total_count}" if offer_page else "no offer page found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Offer Page Creation """

        info_logger.info("Offer Page POST api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Offer Page Created Successfully.")
            return get_response('offer page created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Offer Page Updation """

        info_logger.info("Offer Page PUT api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update offer page', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        parent_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=parent_product_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Offer PageUpdated Successfully.")
            return get_response('offer page updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Offer Page """

        info_logger.info("Offer Page DELETE api called.")
        if not request.data.get('offer_page_ids'):
            return get_response('please select offer page', False)
        try:
            for id in request.data.get('offer_page_ids'):
                offer_page_id = self.queryset.get(id=int(id))
                try:
                    offer_page_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'offer_page_id': offer_page_id}
                    info_logger.info("offer_page deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete offer page {offer_page_id.name}, '
                                        f'because this offer page is mapped with offer', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid offer page {id}', False)
        return get_response('offer page were deleted successfully!', True)

    def offer_page_search(self):

        search_text = self.request.GET.get('search_text')

        # search using name based on criteria that matches
        if search_text:
            self.queryset = offer_page_search(self.queryset, search_text)
        return self.queryset


class OfferBannerSlotView(GenericAPIView):
    """
        Get OfferBannerSlot
        Add OfferBannerSlot
        Search OfferBannerSlot
        List OfferBannerSlot
        Update OfferBannerSlot
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = OfferBannerSlot.objects.values('id', 'name', 'page').order_by('-id')
    serializer_class = OfferBannerSlotSerializers

    def get(self, request):
        """ GET API for Offer Page """

        info_logger.info("Offer PageGET api called.")
        if request.GET.get('id'):
            """ Get Offer Page for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            offer_page = id_validation['data']
        else:
            """ GET Offer Page List """
            self.queryset = self.offer_page_search()
            offer_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_page, many=True)
        msg = "" if offer_page else "no offer page found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Offer Page Creation """

        info_logger.info("Offer Page POST api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Offer Page Created Successfully.")
            return get_response('offer page created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Offer Page Updation """

        info_logger.info("Offer Page PUT api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update offer page', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        parent_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=parent_product_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Offer PageUpdated Successfully.")
            return get_response('offer page updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Offer Page """

        info_logger.info("Offer Page DELETE api called.")
        if not request.data.get('offer_page_ids'):
            return get_response('please select offer page', False)
        try:
            for id in request.data.get('offer_page_ids'):
                offer_page_id = self.queryset.get(id=int(id))
                try:
                    offer_page_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'offer_page_id': offer_page_id}
                    info_logger.info("offer_page deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete offer page {offer_page_id.name}, '
                                        f'because this offer page is mapped with offer', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid offer page {id}', False)
        return get_response('offer page were deleted successfully!', True)

    def offer_page_search(self):

        search_text = self.request.GET.get('search_text')

        # search using name based on criteria that matches
        if search_text:
            self.queryset = offer_page_search(self.queryset, search_text)
        return self.queryset
