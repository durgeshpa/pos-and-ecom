import logging
from datetime import datetime
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.utils.six import with_metaclass

from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import OfferBannerDataSerializer, OfferPageListSerializers, TopSKUSerializer, OfferPageSerializers, \
    OfferBannerSlotSerializers, TopSKUSerializers, OfferBannerListSlotSerializers, OfferBannerPositionSerializers, \
    OfferBannerListSerializer, OfferBannerSerializers
from offer.models import OfferBannerPosition, OfferBannerData, OfferBannerSlot, OfferPage, TopSKU, OfferBanner

from shops.models import Shop, ParentRetailerMapping
from products.models import Product
from rest_framework import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from retailer_backend.utils import SmallOffsetPagination

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id
from offer.services import offer_banner_offer_page_slot_search, offer_banner_position_search, top_sku_search
from offer.common_validators import validate_data_format
from categories.models import Category
from categories.services import category_search
from products.services import brand_search, child_product_search
from products.api.v1.serializers import CategorySerializers, BrandSerializers, ProductSerializers
from brand.models import Brand

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class GetSlotOfferBannerListView(APIView):
    # queryset = BannerData.objects.filter(slot__position_name=pos_name).order_by('banner_data_id')
    # serializer_class = BannerPositionSerializer
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):

        startdate = datetime.now()
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


class GetPageBannerListView(APIView):
    # queryset = BannerData.objects.filter(slot__position_name=pos_name).order_by('banner_data_id')
    # serializer_class = BannerPositionSerializer
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        startdate = datetime.now()
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

        shop_id = self.request.GET.get('shop_id')
        date = datetime.now()

        if shop_id and shop_id != '-1':
            if Shop.objects.get(id=shop_id).retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
                data = TopSKU.objects.filter(start_date__lte=date, end_date__gte=date, status=True, shop=parent).exclude(offer_top_sku__isnull=True)
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
        Delete OfferPage
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OfferPage.objects.select_related('updated_by', 'created_by') \
        .prefetch_related('offer_page_log', 'offer_page_log__updated_by').only('id', 'name', 'updated_by',
                                                                               'created_by').order_by('-id')
    serializer_class = OfferPageSerializers

    def get(self, request):
        """ GET API for Offer Page """

        info_logger.info("Offer PageGET api called.")
        offer_page_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Offer Page for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            offer_page = id_validation['data']
        else:
            """ GET Offer Page List """
            self.queryset = self.offer_page_search()
            offer_page_total_count = self.queryset.count()
            offer_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_page, many=True)
        msg = f"total count {offer_page_total_count}" if offer_page else "no offer page found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Offer Page Creation """

        info_logger.info("Offer Page POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Offer Page Created Successfully.")
            return get_response('offer page created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Offer Page Updation """

        info_logger.info("Offer Page PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update offer page', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        offer_page_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=offer_page_instance, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Offer Page Updated Successfully.")
            return get_response('offer page updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Offer Page """

        info_logger.info("Offer Page DELETE api called.")
        if not request.data.get('offer_page_ids'):
            return get_response('please select atleast one offer page', False)
        try:
            for off_id in request.data.get('offer_page_ids'):
                offer_page_id = self.queryset.get(id=int(off_id))
                try:
                    offer_page_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(), 'offer_page': offer_page_id}
                    info_logger.info("offer_page deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete offer page {offer_page_id.name}, '
                                        f'because this offer page is mapped with offer', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid offer page {off_id}', False)
        return get_response('offer page were deleted successfully!', True)

    def offer_page_search(self):
        search_text = self.request.GET.get('search_text')
        # search using name based on criteria that matches
        if search_text:
            self.queryset = offer_banner_offer_page_slot_search(self.queryset, search_text)
        return self.queryset


class OfferPageListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OfferPage.objects.values('id', 'name').order_by('-id')
    serializer_class = OfferPageListSerializers

    def get(self, request):
        """ GET API for List Offer Page """
        info_logger.info("List Offer PageGET api called.")
        """ GET Offer Page List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = offer_banner_offer_page_slot_search(self.queryset, search_text)
        offer_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_page, many=True)
        msg = "" if offer_page else "no offer page found"
        return get_response(msg, serializer.data, True)


class OfferBannerSlotView(GenericAPIView):
    """
        Get OfferBannerSlot
        Add OfferBannerSlot
        Search OfferBannerSlot
        List OfferBannerSlot
        Update OfferBannerSlot
        Delete OfferBannerSlot
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OfferBannerSlot.objects.select_related('updated_by', 'created_by', 'page') \
        .prefetch_related('offer_banner_slot_log', 'offer_banner_slot_log__updated_by') \
        .only('id', 'name', 'page', 'updated_by', 'created_by').order_by('-id')
    serializer_class = OfferBannerSlotSerializers

    def get(self, request):
        """ GET API for Offer Banner Slot """

        info_logger.info("Offer Banner Slot GET api called.")
        offer_banner_slot_total_count = self.queryset.count()

        if request.GET.get('id'):
            """ Get Offer Banner Slot for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            offer_banner_slot = id_validation['data']
        else:
            """ GET Offer Banner Slot List """
            self.queryset = self.offer_banner_slot_search_filter()
            offer_banner_slot_total_count = self.queryset.count()
            offer_banner_slot = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(offer_banner_slot, many=True)
        msg = f"total count {offer_banner_slot_total_count}" if offer_banner_slot else "no offer banner slot found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Offer Banner Slot Creation """

        info_logger.info("Offer Banner Slot POST api called.")

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Offer Banner Slot Created Successfully.")
            return get_response('offer banner slot created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Offer Banner Slot Updation """

        info_logger.info("Offer Banner Slot PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update offer banner slot', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        offer_banner_slot = id_instance['data'].last()
        serializer = self.serializer_class(instance=offer_banner_slot, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Offer Banner Slot Updated Successfully.")
            return get_response('offer banner slot updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Offer Banner Slot """

        info_logger.info("Offer Banner Slot DELETE api called.")
        if not request.data.get('offer_banner_slot_ids'):
            return get_response('please select offer banner slot', False)
        try:
            for id in request.data.get('offer_banner_slot_ids'):
                offer_banner_slot_id = self.queryset.get(id=int(id))
                try:
                    offer_banner_slot_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'offer_banner_slot': offer_banner_slot_id}
                    info_logger.info("offer_banner_slot deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete offer banner slot {offer_banner_slot_id.name}, '
                                        f'because this offer banner slot is mapped with offer', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid offer banner slot {id}', False)
        return get_response('offer banner slot were deleted successfully!', True)

    def offer_banner_slot_search_filter(self):

        search_text = self.request.GET.get('search_text')
        page = self.request.GET.get('page')
        # search using name based on criteria that matches
        if search_text:
            self.queryset = offer_banner_offer_page_slot_search(self.queryset, search_text)
        # filter based on page
        if page is not None:
            self.queryset = self.queryset.filter(page_id=page)

        return self.queryset


class TopSKUView(GenericAPIView):
    """
        Get TopSKU
        Add TopSKU
        Search TopSKU
        List TopSKU
        Update TopSKU
        Delete TopSKU
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = TopSKU.objects.select_related('updated_by', 'created_by', 'shop') \
        .prefetch_related('top_sku_log', 'top_sku_log__updated_by', 'shop__shop_type', 'shop__shop_owner').\
        only('id', 'updated_by', 'created_by', 'shop', 'start_date', 'end_date', 'status').order_by('-id')
    serializer_class = TopSKUSerializers

    def get(self, request):
        """ GET API for TopSKU """

        info_logger.info("TopSKU api called.")
        offer_page_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get TopSKU for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            offer_page = id_validation['data']
        else:
            """ GET TopSKU List """
            self.queryset = self.top_sku_search_filter()
            offer_page_total_count = self.queryset.count()
            offer_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_page, many=True)
        msg = f"total count {offer_page_total_count}" if offer_page else "no top sku found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for TopSKU Creation """

        info_logger.info("TopSKU POST api called.")
        try:
            products = request.data.pop('products')
        except Exception as e:
            return get_response('Please select products', False)
        serializer = self.serializer_class(data=request.data, context = {'products':products})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("TopSKU Created Successfully.")
            return get_response('top sku created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)
        
        
    def put(self, request):
        """ PUT API for TopSKU Updation """

        info_logger.info("TopSKU PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update top sku', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        top_sku_instance = id_instance['data'].last()
        products = None
        if 'products' in request.data:
            products = request.data.pop('products')
        serializer = self.serializer_class(instance=top_sku_instance, data=request.data, context = {'products':products})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Top SKU Updated Successfully.")
            return get_response('top sku updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Top SKU """

        info_logger.info("Top SKU DELETE api called.")
        if not request.data.get('top_sku_ids'):
            return get_response('please select atleast one top sku', False)
        try:
            for off_id in request.data.get('top_sku_ids'):
                top_sku_id = self.queryset.get(id=int(off_id))
                try:
                    top_sku_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(), 'top_sku_id': top_sku_id}
                    info_logger.info("top_sku deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete top sku {top_sku_id.name}, '
                                        f'because this top sku  is mapped with offer', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid top sku {off_id}', False)
        return get_response('top sku were deleted successfully!', True)

    def top_sku_search_filter(self):
        seller_shop_id = self.request.GET.get('seller_shop_id')
        product_id = self.request.GET.get('product_id')
        status = self.request.GET.get('status')
        start_date_range_from = self.request.GET.get('start_date_range_from')
        start_date_range_to = self.request.GET.get('start_date_range_to')
        end_date_range_from = self.request.GET.get('end_date_range_from')
        end_date_range_to = self.request.GET.get('end_date_range_to')
        search_text = self.request.GET.get('search_text')
        # search using name based on criteria that matches
        if search_text:
            self.queryset = top_sku_search(self.queryset, search_text)

        if product_id is not None:
            self.queryset = self.queryset.filter(product_id=product_id)
        if seller_shop_id is not None:
            self.queryset = self.queryset.filter(seller_shop_id=seller_shop_id)
        if status is not None:
            self.queryset = self.queryset.filter(status=status)

        if start_date_range_from:
            self.queryset = self.queryset.filter(start_date__date__gte=start_date_range_from)
        if start_date_range_to:
            self.queryset = self.queryset.filter(start_date__date__lte=start_date_range_to)
        if end_date_range_from:
            self.queryset = self.queryset.filter(end_date__date__gte=end_date_range_from)
        if end_date_range_to:
            self.queryset = self.queryset.filter(end_date__date__lte=end_date_range_to)

        return self.queryset


class OfferBannerSlotListView(GenericAPIView):
    """
        Get OfferBannerSlot List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OfferBannerSlot.objects.select_related('page', ).only('id', 'name', 'page', ).order_by('-id')
    serializer_class = OfferBannerListSlotSerializers

    def get(self, request):
        """ GET API for Offer Banner Slot """

        info_logger.info("Offer Banner Slot GET List api called.")
        """ GET Offer Banner Slot List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = offer_banner_offer_page_slot_search(self.queryset, search_text)
        offer_banner_slot = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_banner_slot, many=True)
        msg = " " if offer_banner_slot else "no offer banner slot found"
        return get_response(msg, serializer.data, True)


class OfferBannerPositionView(GenericAPIView):
    """
        Get OfferBannerPosition
        Add OfferBannerPosition
        Search OfferBannerPosition
        List OfferBannerPosition
        Update OfferBannerPosition
        Delete OfferBannerPosition
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OfferBannerPosition.objects.select_related('shop', 'offerbannerslot', 'offerbannerslot__page',
                                                          'page', 'shop__shop_type', 'shop__shop_owner'). \
        prefetch_related('offer_ban_data').only('id', 'shop', 'page', 'offer_banner_position_order',
                                                'offerbannerslot').order_by('-id')
    serializer_class = OfferBannerPositionSerializers

    def get(self, request):
        """ GET API for Offer Banner Position """

        info_logger.info("Offer Banner Position GET api called.")
        offer_banner_position_total_count = self.queryset.count()

        if request.GET.get('id'):
            """ Get Offer Banner Position for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            offer_banner_slot = id_validation['data']
        else:
            """ GET Offer Banner Position List """
            self.queryset = self.offer_banner_position_search_filter()
            offer_banner_position_total_count = self.queryset.count()
            offer_banner_slot = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(offer_banner_slot, many=True)
        msg = f"total count {offer_banner_position_total_count}" if offer_banner_slot else \
            "no offer banner position found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Offer Banner Slot Creation """

        info_logger.info("Offer Banner Slot POST api called.")

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            info_logger.info("Offer Banner Position Created Successfully.")
            return get_response('offer banner position created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Offer Banner Position Updation """

        info_logger.info("Offer Banner Position PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update offer banner position', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        offer_banner_slot = id_instance['data'].last()
        serializer = self.serializer_class(instance=offer_banner_slot, data=request.data)
        if serializer.is_valid():
            serializer.save()
            info_logger.info("Offer Banner Position Updated Successfully.")
            return get_response('offer banner position updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Offer Banner Position """

        info_logger.info("Offer Banner Position DELETE api called.")
        if not request.data.get('offer_banner_position_ids'):
            return get_response('please select offer banner position', False)
        try:
            for o_id in request.data.get('offer_banner_position_ids'):
                offer_banner_position_id = self.queryset.get(id=int(o_id))
                try:
                    offer_banner_position_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'offer_banner_position': offer_banner_position_id}
                    info_logger.info("offer_banner_position deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete offer banner position {offer_banner_position_id}, '
                                        f'because this offer banner position is mapped with offer', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid offer banner position {o_id}', False)
        return get_response('offer banner position were deleted successfully!', True)

    def offer_banner_position_search_filter(self):

        search_text = self.request.GET.get('search_text')
        page = self.request.GET.get('page')
        # search using name based on criteria that matches
        if search_text:
            self.queryset = offer_banner_position_search(self.queryset, search_text)
        # filter based on page
        if page is not None:
            self.queryset = self.queryset.filter(page_id=page)

        return self.queryset


class OfferBannerListView(GenericAPIView):
    """
        Get OfferBanner List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OfferBanner.objects.only('id', 'name', ).order_by('-id')
    serializer_class = OfferBannerListSerializer

    def get(self, request):
        """ GET API for Offer Banner """

        info_logger.info("Offer Banne GET List api called.")
        """ GET Offer Banner List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = offer_banner_offer_page_slot_search(self.queryset, search_text)
        offer_banner = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_banner, many=True)
        msg = " " if offer_banner else "no offer banner found"
        return get_response(msg, serializer.data, True)


class OfferBannerTypeView(GenericAPIView):
    """
        Get Offer Banner Type List
    """
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET Choice List for BANNER_TYPE """

        info_logger.info("BANNER TYPE GET api called.")
        """ GET BANNER TYPE Choice List """
        fields = ['offer_banner_type', ]
        data = [dict(zip(fields, d)) for d in OfferBanner.BANNER_TYPE]
        msg = ""
        return get_response(msg, data, True)


class OfferBannerView(GenericAPIView):
    """
        Get OfferBanner List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = OfferBanner.objects.select_related('updated_by', 'category', 'sub_category', 'brand', 'sub_brand', ) \
        .prefetch_related('products', 'offer_banner_log', 'offer_banner_log__updated_by') \
        .only('id', 'name', 'image', 'offer_banner_type', 'category', 'sub_category', 'brand', 'sub_brand', 'products',
              'status', 'offer_banner_start_date', 'offer_banner_end_date', 'updated_by', 'created_at').order_by('-id')
    serializer_class = OfferBannerSerializers

    def get(self, request):
        """ GET API for Offer Banner """

        info_logger.info("Offer Banner api called.")
        offer_banner_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Offer Banner for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            offer_page = id_validation['data']
        else:
            """ GET Offer Banner List """
            self.queryset = self.offer_banner_search_filter()
            offer_banner_total_count = self.queryset.count()
            offer_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(offer_page, many=True)
        msg = f"total count {offer_banner_total_count}" if offer_page else "no offer banner found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Offer Banner Creation """

        info_logger.info("Offer Banner POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Offer Banner Created Successfully.")
            return get_response('offer banner created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Offer Banner Updation """

        info_logger.info("Offer Banner PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update offer banner', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        offer_banner_slot = id_instance['data'].last()

        serializer = self.serializer_class(instance=offer_banner_slot, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Offer Banner Updated Successfully.")
            return get_response('offer banner updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Offer Banner """

        info_logger.info("Offer Banner DELETE api called.")
        if not request.data.get('offer_banner_ids'):
            return get_response('please select offer banner', False)
        try:
            for o_id in request.data.get('offer_banner_ids'):
                offer_banner_id = self.queryset.get(id=int(o_id))
                try:
                    offer_banner_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'offer_banner_ids': offer_banner_id}
                    info_logger.info("offer_banner deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete offer banner {offer_banner_id.name}, '
                                        f'because this offer banner is mapped with offer', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid offer banner {o_id}', False)
        return get_response('offer banner were deleted successfully!', True)

    def offer_banner_search_filter(self):

        search_text = self.request.GET.get('search_text')
        # search using name based on criteria that matches
        if search_text:
            self.queryset = offer_banner_offer_page_slot_search(self.queryset, search_text)

        return self.queryset


class ParentCategoryList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Category.objects.filter(category_parent=None)
    serializer_class = CategorySerializers

    def get(self, request):
        """ GET API for Category"""

        """ GET API for Category LIST """
        search_text = self.request.GET.get('search_text')
        # search based on category name
        if search_text:
            self.queryset = category_search(self.queryset, search_text.strip())
        category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        msg = "" if category else "no category found"
        return get_response(msg, serializer.data, True)


class ChildCategoryList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Category.objects.filter(category_parent__isnull=False)
    serializer_class = CategorySerializers

    def get(self, request):
        """ GET API for Category LIST with SubCategory """
        search_text = self.request.GET.get('search_text')
        # search based on category name
        if search_text:
            self.queryset = category_search(self.queryset, search_text.strip())
        category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        msg = "" if category else "no category found"
        return get_response(msg, serializer.data, True)


class ParentBrandListView(GenericAPIView):
    """
        Get Brand List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.filter(brand_parent=None)
    serializer_class = BrandSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = brand_search(self.queryset, search_text)
        brand = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(brand, many=True)
        msg = "" if brand else "no brand found"
        return get_response(msg, serializer.data, True)


class ChildBrandListView(GenericAPIView):
    """
        Get Brand List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.filter(brand_parent__isnull=False)
    serializer_class = BrandSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = brand_search(self.queryset, search_text)
        brand = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(brand, many=True)
        msg = "" if brand else "no brand found"
        return get_response(msg, serializer.data, True)


class ProductListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Product.objects.order_by('-id')

    serializer_class = ProductSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text)
        child_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(child_product, many=True)
        msg = "" if child_product else "no product found"
        return get_response(msg, serializer.data, True)
