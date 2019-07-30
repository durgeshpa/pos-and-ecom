import datetime
import logging

from dal import autocomplete
from wkhtmltopdf.views import PDFTemplateResponse

from django.forms import formset_factory, inlineformset_factory, modelformset_factory, BaseFormSet, ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Q, F
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save

from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from celery.task import task

from sp_to_gram.models import (
    OrderedProductReserved, OrderedProductMapping as SPOrderedProductMapping,
    OrderedProduct as SPOrderedProduct)
from retailer_to_sp.models import (
    Cart, CartProductMapping, Order, OrderedProduct, OrderedProductMapping,
    CustomerCare, Payment, Return, ReturnProductMapping, Note, Trip, Dispatch,
    ShipmentRescheduling
)
from products.models import Product
from retailer_to_sp.forms import (
    OrderedProductForm, OrderedProductMappingShipmentForm,
    OrderedProductMappingDeliveryForm, OrderedProductDispatchForm,
    TripForm, DispatchForm, DispatchDisabledForm
)
from django.views.generic import TemplateView
from django.conf import settings
from django.contrib import messages

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from shops.models import Shop
from retailer_to_sp.api.v1.serializers import (
    DispatchSerializer, CommercialShipmentSerializer, OrderedCartSerializer
)
import json
from django.http import HttpResponse
from django.core import serializers
from retailer_to_sp.tasks import (update_reserved_order,)


logger = logging.getLogger(__name__)
from retailer_to_sp.api.v1.serializers import OrderedCartSerializer
from django.urls import reverse
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from retailer_backend.common_function import brand_credit_note_pattern
from addresses.models import Address


class ReturnProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Product.objects.all()
        invoice_no_id = self.forwarded.get('invoice_no', None)

        if invoice_no_id:
            ordered_product = OrderedProduct.objects.get(id=invoice_no_id)
            returned_products = ordered_product.\
                rt_order_product_order_product_mapping.all().values('product')
            qs = qs.filter(id__in=[returned_products]).order_by('product_name')
        else:
            qs = None

        if self.q:
            qs = qs.filter(product_name__istartswith=self.q)
        return qs


class DownloadCreditNote(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'credit_note.pdf'
    template_name = 'admin/credit_note/credit_note.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(Return, pk=self.kwargs.get('pk'))
        pk = self.kwargs.get('pk')
        a = Return.objects.get(pk=pk)
        shop = a
        products = a.rt_product_return_product_mapping.all()
        order_id = a.invoice_no.order.order_no
        sum_qty = 0
        sum_amount = 0
        tax_inline = 0
        taxes_list = []
        gst_tax_list = []
        cess_tax_list = []
        surcharge_tax_list = []
        for z in shop.invoice_no.order.seller_shop.\
                shop_name_address_mapping.all():
            shop_name_gram = z.shop_name
            nick_name_gram = z.nick_name
            address_line1_gram = z.address_line1
            city_gram = z.city
            state_gram = z.state
            pincode_gram = z.pincode

        for m in products:
            sum_qty = sum_qty + (
                int(m.returned_product.product_inner_case_size) *
                int(m.total_returned_qty)
            )
            for h in m.get_shop_specific_products_prices_sp_return():
                sum_amount = sum_amount + (
                        int(m.returned_product.product_inner_case_size) *
                        int(m.total_returned_qty) *
                        h.price_to_retailer
                )
                inline_sum_amount = (
                        int(m.returned_product.product_inner_case_size) *
                        int(m.total_returned_qty) *
                        h.price_to_retailer
                )
            for n in m.returned_product.product_pro_tax.all():
                divisor = (1+(n.tax.tax_percentage/100))
                original_amount = (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type == 'gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type == 'cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type == 'surcharge':
                    surcharge_tax_list.append(tax_amount)

                taxes_list.append(tax_amount)
                igst = sum(gst_tax_list)
                cgst = (sum(gst_tax_list))/2
                sgst = (sum(gst_tax_list))/2
                cess = sum(cess_tax_list)
                surcharge = sum(surcharge_tax_list)

        total_amount = sum_amount
        total_amount_int = int(total_amount)


        data = {
            "object": order_obj,
            "products": products,
            "shop": shop,
            "total_amount_int": total_amount_int,
            "sum_qty": sum_qty,
            "sum_amount": sum_amount,
            "url": request.get_host(),
            "scheme": request.is_secure() and "https" or "http",
            "igst": igst,
            "cgst": cgst,
            "sgst": sgst,
            "cess": cess,
            "surcharge": surcharge,
            "total_amount": total_amount,
            "order_id": order_id,
            "shop_name_gram": shop_name_gram,
            "nick_name_gram": nick_name_gram,
            "city_gram": city_gram,
            "address_line1_gram": address_line1_gram,
            "pincode_gram": pincode_gram,
            "state_gram": state_gram
        }

        cmd_option = {
            "margin-top": 10,
            "zoom": 1,
            "javascript-delay": 1000,
            "footer-center": "[page]/[topage]",
            "no-stop-slow-scripts": True,
            "quiet": True
        }
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )
        return response


class RequiredFormSet(BaseFormSet):

    def clean(self):
        to_ship_sum = []
        for form in self.forms:
            to_ship_pieces = form.cleaned_data.get('shipped_qty')
            if to_ship_pieces:
                to_ship_sum.append(to_ship_pieces)
        if sum(to_ship_sum) == 0:
            raise ValidationError("Please add shipment quantity for at least one product")


def ordered_product_mapping_shipment(request):
    order_id = request.GET.get('order_id')
    ordered_product_set = formset_factory(OrderedProductMappingShipmentForm,
                                          extra=0, max_num=1, formset=RequiredFormSet
                                          )
    form = OrderedProductForm()
    form_set = ordered_product_set()
    if order_id and request.method == 'GET':
        cart_id = Order.objects \
            .values_list('ordered_cart', flat=True) \
            .get(pk=order_id)
        cart_products = CartProductMapping.objects \
            .values('cart_product', 'cart_product__product_name',
                    'no_of_pieces') \
            .filter(cart_id=cart_id)
        cart_products = list(cart_products)

        shipment_products = OrderedProductMapping.objects \
            .values('product') \
            .filter(
                ordered_product__order_id=order_id,
                product_id__in=[i['cart_product'] for i in cart_products]) \
            .annotate(Sum('delivered_qty'), Sum('shipped_qty'))
        products_list = []
        for item in cart_products:
            shipment_product = list(filter(lambda product: product['product'] == item['cart_product'],
                                           shipment_products))
            if shipment_product:
                shipment_product_dict = shipment_product[0]
                already_shipped_qty = shipment_product_dict.get('delivered_qty__sum')
                to_be_shipped_qty = shipment_product_dict.get('shipped_qty__sum')
                ordered_no_pieces = item['no_of_pieces']
                if ordered_no_pieces != to_be_shipped_qty:
                    products_list.append({
                        'product': item['cart_product'],
                        'product_name': item['cart_product__product_name'],
                        'ordered_qty': ordered_no_pieces,
                        'already_shipped_qty': already_shipped_qty,
                        'to_be_shipped_qty': to_be_shipped_qty
                    })
            else:
                products_list.append({
                    'product': item['cart_product'],
                    'product_name': item['cart_product__product_name'],
                    'ordered_qty': item['no_of_pieces'],
                    'already_shipped_qty': 0,
                    'to_be_shipped_qty': 0
                })
        form_set = ordered_product_set(initial=products_list)
        form = OrderedProductForm(initial={'order': order_id})

    if request.method == 'POST':
        form_set = ordered_product_set(request.POST)
        form = OrderedProductForm(request.POST)
        if form.is_valid() and form_set.is_valid():
            try:
                with transaction.atomic():
                    shipment = form.save()
                    # shipment.shipment_status = 'SHIPMENT_CREATED'
                    # shipment.save()
                    for forms in form_set:
                        if forms.is_valid():
                            to_be_ship_qty = forms.cleaned_data.get('shipped_qty', 0)
                            product_name = forms.cleaned_data.get('product')
                            if to_be_ship_qty:
                                formset_data = forms.save(commit=False)
                                formset_data.ordered_product = shipment
                                max_pieces_allowed = int(formset_data.ordered_qty) - int(formset_data.shipped_qty_exclude_current)
                                if max_pieces_allowed < int(to_be_ship_qty):
                                    raise Exception('{}: Max Qty allowed is {}'.format(product_name, max_pieces_allowed))
                                formset_data.save()
                    update_reserved_order.delay(json.dumps({'shipment_id': shipment.id}))
                return redirect('/admin/retailer_to_sp/shipment/')

            except Exception as e:
                messages.error(request, e)
                logger.exception("An error occurred while creating shipment {}".format(e))

    return render(
        request,
        'admin/retailer_to_sp/OrderedProductMappingShipment.html',
        {'ordered_form': form, 'formset': form_set}
    )


def trip_planning(request):

    if request.method == 'POST':

        form = TripForm(request.user, request.POST)
        if form.is_valid():
            trip = form.save()
            selected_shipments = form.cleaned_data.get('selected_id', None)
            if selected_shipments:
                selected_shipments = selected_shipments.split(',')
                selected_shipments = Dispatch.objects.filter(
                                                    pk__in=selected_shipments)
                for shipment_instance in selected_shipments:
                    shipment_instance.trip = trip
                    shipment_instance.shipment_status = 'READY_TO_DISPATCH'
                    shipment_instance.save()
            return redirect('/admin/retailer_to_sp/trip/')
        else:
            form = TripForm(request.user, request.POST)
    else:
        form = TripForm(request.user)

    return render(
        request,
        'admin/retailer_to_sp/TripPlanning.html',
        {'form': form}
    )


def trip_planning_change(request, pk):
    trip_instance = Trip.objects.get(pk=pk)
    trip_status = trip_instance.trip_status

    if request.method == 'POST':
        form = TripForm(request.user, request.POST, instance=trip_instance)
        if (trip_status == 'READY' or trip_status == 'STARTED' or
                trip_status == 'CANCELLED'):
            if form.is_valid():
                trip = form.save()
                current_trip_status = trip.trip_status
                selected_shipment_ids = form.cleaned_data.get('selected_id', None)
                unselected_shipment_ids = form.cleaned_data.get('unselected_id', None)

                if selected_shipment_ids:
                    selected_shipments = selected_shipment_ids.split(',')
                    selected_shipments = Dispatch.objects.filter(~Q(shipment_status='CANCELLED'), pk__in=selected_shipments)
                    for shipment_instance in selected_shipments:
                        if current_trip_status == 'READY':
                            shipment_instance.trip = trip
                            shipment_instance.shipment_status = 'READY_TO_DISPATCH'

                        elif shipment_instance.trip == trip and current_trip_status == 'STARTED':
                            shipment_instance.shipment_status = 'OUT_FOR_DELIVERY'

                        elif current_trip_status == 'COMPLETED':
                            ordered_product_mapping = OrderedProductMapping \
                                .objects.filter(
                                    ordered_product=shipment_instance
                                ).update(
                                    delivered_qty=F('shipped_qty')
                                )
                            shipment_instance.shipment_status = 'FULLY_DELIVERED_AND_COMPLETED'
                            update_order_status(
                                close_order_checked=False,
                                shipment_id=shipment_instance.id
                            )
                        elif current_trip_status == 'CANCELLED':
                            if shipment_instance.trip:
                                shipment_instance.trip = None
                                shipment_instance.shipment_status = 'READY_TO_SHIP'
                        shipment_instance.save()

                if unselected_shipment_ids and current_trip_status == 'READY':
                    unselected_shipments = unselected_shipment_ids.split(',')
                    unselected_shipments = Dispatch.objects.filter(
                                                pk__in=unselected_shipments)
                    for shipment_instance in unselected_shipments:
                        if shipment_instance.trip:
                            shipment_instance.trip = None
                            shipment_instance.shipment_status = 'READY_TO_SHIP'
                            shipment_instance.save()
                return redirect('/admin/retailer_to_sp/trip/')
            else:
                form = TripForm(request.user, request.POST, instance=trip_instance)
    else:
        form = TripForm(request.user, instance=trip_instance)
    return render(
        request,
        'admin/retailer_to_sp/TripPlanningChange.html',
        {'form': form}
    )


class LoadDispatches(APIView):
    """Return list of dispatches for specific seller shop

    :param request: seller_shop_id
    :return: list of dispatch
    """
    permission_classes = (AllowAny,)

    def get(self, request):

        seller_shop = request.GET.get('seller_shop_id')
        area = request.GET.get('area')
        trip_id = request.GET.get('trip_id')
        commercial = request.GET.get('commercial')
        vector = SearchVector('order__shipping_address__address_line1')
        query = SearchQuery(area)
        similarity = TrigramSimilarity(
                            'order__shipping_address__address_line1', area)

        if seller_shop and area and trip_id:
            dispatches = Dispatch.objects.annotate(
                            rank=SearchRank(vector, query) + similarity
                            ).filter(
                                Q(shipment_status='READY_TO_SHIP') |
                                Q(shipment_status='RESCHEDULED') |
                                Q(trip=trip_id), order__seller_shop=seller_shop
                                ).order_by('-rank')

        elif seller_shop and trip_id:
            dispatches = Dispatch.objects.filter(
                            Q(shipment_status='READY_TO_SHIP') |
                            Q(shipment_status='RESCHEDULED') |
                            Q(trip=trip_id), order__seller_shop=seller_shop)

        elif trip_id:
            dispatches = Dispatch.objects.filter(trip=trip_id)

        elif seller_shop and area:
            dispatches = Dispatch.objects.annotate(
                rank=SearchRank(vector, query) + similarity
            ).filter(
                Q(shipment_status=OrderedProduct.READY_TO_SHIP) |
                Q(shipment_status=OrderedProduct.RESCHEDULED),
                order__seller_shop=seller_shop
            ).order_by('-rank')

        elif seller_shop:
            dispatches = Dispatch.objects.select_related(
                'order', 'order__shipping_address', 'order__ordered_cart'
            ).filter(
                Q(shipment_status=OrderedProduct.READY_TO_SHIP) |
                Q(shipment_status=OrderedProduct.RESCHEDULED),
                order__seller_shop=seller_shop
            ).order_by('invoice_no')

        elif area and trip_id:
            dispatches = Dispatch.objects.annotate(
                            rank=SearchRank(vector, query) + similarity
                            ).filter(Q(shipment_status='READY_TO_SHIP') |
                                    Q(shipment_status=OrderedProduct.RESCHEDULED) |
                                     Q(trip=trip_id)).order_by('-rank')

        elif area:
            dispatches = Dispatch.objects.annotate(
                            rank=SearchRank(vector, query) + similarity
                            ).order_by('-rank')

        else:
            dispatches = Dispatch.objects.none()

        reschedule_dispatches = ShipmentRescheduling.objects.values_list(
            'shipment', flat=True
        ).filter(
            ~Q(rescheduling_date__lte=datetime.date.today()),
            shipment__shipment_status=OrderedProduct.RESCHEDULED
        )
        dispatches = dispatches.exclude(id__in=reschedule_dispatches)

        if dispatches and commercial:
            serializer = CommercialShipmentSerializer(dispatches, many=True)
            msg = {'is_success': True,
                   'message': None,
                   'response_data': serializer.data}
        elif dispatches:
            serializer = DispatchSerializer(dispatches, many=True)
            msg = {'is_success': True,
                   'message': None,
                   'response_data': serializer.data}
        else:
            msg = {'is_success': False,
                   'message': ("There are no shipments that"
                               " are Ready to Ship(QC Passed)"),
                   'response_data': None}
        return Response(msg, status=status.HTTP_201_CREATED)



def load_dispatches(request):
    """Return list of dispatches for specific seller shop

    :param request: seller_shop_id
    :return: list of dispatch
    """
    seller_shop = request.GET.get('seller_shop_id')
    area = request.GET.get('area')
    trip_id = request.GET.get('trip_id')

    vector = SearchVector('order__shipping_address__address_line1')
    query = SearchQuery(area)
    similarity = TrigramSimilarity('order__shipping_address__address_line1', area)

    if seller_shop and area and trip_id:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).filter(Q(shipment_status='READY_TO_SHIP') |
                                 Q(trip=trip_id), order__seller_shop=seller_shop).order_by('-rank')

    elif seller_shop and trip_id:
        dispatches = Dispatch.objects.filter(Q(shipment_status='READY_TO_SHIP') |
                                             Q(trip=trip_id), order__seller_shop=seller_shop)
    elif seller_shop and area:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).filter(shipment_status='READY_TO_SHIP', order__seller_shop=seller_shop).order_by('-rank')

    elif seller_shop:
        dispatches = Dispatch.objects.select_related('order').filter(shipment_status='READY_TO_SHIP',
                                             order__seller_shop=seller_shop)
        #serializer = DispatchSerializer(dispatches, many=True)
        #msg = {'is_success': True, 'message': ['All Messages'], 'response_data': serializer.data}
        #return Response(msg, status=status.HTTP_201_CREATED)
        data = serializers.serialize('json', dispatches)
        #return JsonResponse(dispatches, safe=False)
        return HttpResponse(data, content_type="application/json")
        #return render(request, 'admin/retailer_to_sp/trip/JSONDispatchesList.html', data)

    elif area and trip_id:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).filter(Q(shipment_status='READY_TO_SHIP') |
                                 Q(trip=trip_id)).order_by('-rank')

    elif area:
        dispatches = Dispatch.objects.annotate(
                        rank=SearchRank(vector, query) + similarity
                        ).order_by('-rank')
    else:
        dispatches = Dispatch.objects.none()
    TripDispatchFormset = modelformset_factory(
        Dispatch,
        fields=[
            'selected', 'items', 'shipment_status', 'invoice_date', 'order', 'shipment_address'
        ],
        form=DispatchForm, extra=0
    )
    formset = TripDispatchFormset(queryset=dispatches)
    return render(
        request, 'admin/retailer_to_sp/DispatchesList.html',
        {'formset': formset}
    )


class DownloadPickList(TemplateView,):
    """
    PDF Download Pick List
    """
    filename = 'pick_list.pdf'
    template_name = 'admin/download/retailer_sp_pick_list.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin/login/?next=%s' % request.path)

        order_obj = get_object_or_404(Order, pk=self.kwargs.get('pk'))
        cart_products = order_obj.ordered_cart.rt_cart_list.all()
        cart_product_list = []

        for cart_pro in cart_products:
            product_list = {
                "product_name": cart_pro.cart_product.product_name,
                "product_sku": cart_pro.cart_product.product_sku,
                "product_mrp": round(cart_pro.get_cart_product_price(order_obj.seller_shop).mrp,2),
                "ordered_qty":cart_pro.qty,
                "no_of_pieces":cart_pro.no_of_pieces,
            }
            cart_product_list.append(product_list)

        data = {
            "order_obj": order_obj,
            "cart_products":cart_product_list,
            "buyer_shop":order_obj.ordered_cart.buyer_shop.shop_name,
            "buyer_contact_no":order_obj.ordered_cart.buyer_shop.shop_owner.phone_number,
            "buyer_shipping_address":order_obj.shipping_address.address_line1,
            "buyer_shipping_city":order_obj.shipping_address.city.city_name,
        }
        cmd_option = {
            "margin-top": 10,
            "zoom": 1,
            "footer-center":
            "[page]/[topage]",
            "no-stop-slow-scripts": True
        }
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option)
        return response


def order_invoices(request):
    order_id = request.GET.get('order_id')
    if order_id:
        invoices = OrderedProduct.objects.filter(
            order_id=order_id
        )
    else:
        invoices = OrderedProduct.objects.none()
    return render(
        request,
        'admin/retailer_to_sp/invoices_dropdown_list.html',
        {'invoices': invoices}
    )


def update_delivered_qty(instance, inline_form):

    instance.delivered_qty = instance.shipped_qty - (
        inline_form.cleaned_data.get('returned_qty', 0)+
        inline_form.cleaned_data.get('damaged_qty', 0)
    )
    instance.save()


def update_shipment_status(form_instance, formset):
    shipped_qty_list = []
    returned_qty_list = []
    damaged_qty_list = []
    for inline_form in formset:
        instance = getattr(inline_form, 'instance', None)
        update_delivered_qty(instance, inline_form)
        shipped_qty_list.append(instance.shipped_qty if instance else 0)
        returned_qty_list.append(inline_form.cleaned_data.get('returned_qty', 0))
        damaged_qty_list.append(inline_form.cleaned_data.get('damaged_qty', 0))

    shipped_qty = sum(shipped_qty_list)
    returned_qty = sum(returned_qty_list)
    damaged_qty = sum(damaged_qty_list)

    if shipped_qty == (returned_qty + damaged_qty):
        form_instance.shipment_status = 'FULLY_RETURNED_AND_COMPLETED'

    elif (returned_qty + damaged_qty) == 0:
        form_instance.shipment_status = 'FULLY_DELIVERED_AND_COMPLETED'

    elif shipped_qty > (returned_qty + damaged_qty):
        form_instance.shipment_status = 'PARTIALLY_DELIVERED_AND_COMPLETED'

    form_instance.save()


def update_order_status(close_order_checked, shipment_id):
    shipment = OrderedProduct.objects.get(pk=shipment_id)
    current_order_shipments = shipment.order.rt_order_order_product \
        .values_list('id', flat=True)

    shipment_products_dict = OrderedProductMapping.objects \
        .values('product', 'ordered_product__order__ordered_cart') \
        .filter(ordered_product__in=list(current_order_shipments)) \
        .annotate(Sum('delivered_qty'), Sum('shipped_qty'),
                  Sum('returned_qty'), Sum('damaged_qty'))

    cart_products_dict = CartProductMapping.objects \
        .values('cart_product', 'no_of_pieces') \
        .filter(cart_product_id__in=[i.get('product')
                                     for i in shipment_products_dict],
                cart_id=shipment_products_dict[0].get(
                    'ordered_product__order__ordered_cart'
        ))

    total_delivered_qty = sum([i.get('delivered_qty__sum')
                               for i in shipment_products_dict])
    total_shipped_qty = sum([i.get('shipped_qty__sum')
                             for i in shipment_products_dict])
    total_returned_qty = sum([i.get('returned_qty__sum')
                              for i in shipment_products_dict])
    total_damaged_qty = sum([i.get('damaged_qty__sum')
                             for i in shipment_products_dict])
    ordered_qty = sum([i.get('no_of_pieces') for i in cart_products_dict])

    order = shipment.order

    if ordered_qty == (total_delivered_qty + total_returned_qty + total_damaged_qty):
        order.order_status = 'SHIPPED'

    elif (total_returned_qty == total_shipped_qty or
          (total_damaged_qty + total_returned_qty) == total_shipped_qty):
        if order.order_closed:
            order.order_status = Order.DENIED_AND_CLOSED
        else:
            order.order_status = 'DENIED'

    elif (total_delivered_qty == 0 and total_shipped_qty > 0 and
            total_returned_qty == 0 and total_damaged_qty == 0):
        order.order_status = 'DISPATCH_PENDING'

    elif (ordered_qty - total_delivered_qty) > 0 and total_delivered_qty > 0:
        if order.order_closed:
            order.order_status = Order.PARTIALLY_SHIPPED_AND_CLOSED
        else:
            order.order_status = 'PARTIALLY_SHIPPED'

    if close_order_checked and not order.order_closed:
        order.order_closed = True

    order.save()


class SellerShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(Q(shop_type__shop_type='sp',shop_owner=self.request.user) | Q(shop_type__shop_type='sp',related_users=self.request.user))

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)
        return qs

class BuyerShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type='r',shop_owner=self.request.user)

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)
        return qs

class DeductReservedQtyFromShipment(object):

    def __init__(self, form, formsets):
        super(DeductReservedQtyFromShipment, self).__init__()
        self.shipment = form
        self.shipment_products = formsets

    def get_cart(self):
        cart = self.shipment.order.ordered_cart
        return cart

    def get_sp_ordered_product_reserved(self, product):
        cart = self.get_cart()
        return OrderedProductReserved.objects.filter(
            cart=cart, product=product, reserved_qty__gt=0).order_by('reserved_qty')

    def deduct_reserved_qty(self, product, ordered_qty, shipped_qty):
        ordered_products_reserved = self.get_sp_ordered_product_reserved(
            product)
        remaining_amount = shipped_qty
        for ordered_product_reserved in ordered_products_reserved:
            if remaining_amount <= 0:
                break
            if ordered_product_reserved.reserved_qty >= remaining_amount:
                deduct_qty = remaining_amount
            else:
                deduct_qty = ordered_product_reserved.reserved_qty

            ordered_product_reserved.reserved_qty -= deduct_qty
            remaining_amount -= deduct_qty
            ordered_product_reserved.save()

    @task
    def update(self):
        for form in self.shipment_products:
            if form.instance.pk:
                product = form.instance.product
                shipped_qty = form.instance.shipped_qty
                ordered_qty = int(form.instance.ordered_qty)
                self.deduct_reserved_qty(product, ordered_qty, shipped_qty)


class UpdateSpQuantity(object):

    def __init__(self, form, formsets):
        super(UpdateSpQuantity, self).__init__()
        self.shipment = form
        self.shipment_products = formsets

    def get_cart(self):
        cart = self.shipment.instance.order.ordered_cart
        return cart

    def get_sp_ordered_product_reserved(self, product):
        cart = self.get_cart()
        return OrderedProductReserved.objects.filter(
            cart=cart, product=product,
            reserved_qty__gt=0).order_by('reserved_qty')

    # def get_shipment_status(self):
    #     shipment_status = self.shipment.instance.shipment_status
    #     return shipment_status

    # def close_order(self):
    #     status = self.shipment.cleaned_data.get('close_order')
    #     return status

    # def update_order_status(self):
    #     self.shipment.instance.order.order_status = self.shipment.instance.\
    #         order.PARTIALLY_SHIPPED_AND_CLOSED
    #     self.shipment.instance.order.save()

    def update_available_qty(self, product):
        ordered_products_reserved = self.get_sp_ordered_product_reserved(
            product)
        for ordered_product_reserved in ordered_products_reserved:
            grn = ordered_product_reserved.order_product_reserved
            grn.available_qty += (ordered_product_reserved.reserved_qty -
                                  ordered_product_reserved.shipped_qty)
            grn.save()
            ordered_product_reserved.save()

    def update(self):
        for inline_form in self.shipment_products:
            for form in inline_form:
                product = form.instance.product
                # if (
                #     self.close_order() and
                #     (self.get_shipment_status() !=
                #      self.shipment.instance.CLOSED)):
                #     self.update_order_status()
                self.update_available_qty(product)

class DownloadTripPdf(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'trip.pdf'
    template_name = 'admin/trip/trip.html'

    def get(self, request, *args, **kwargs):
        trip_obj = get_object_or_404(Trip, pk=self.kwargs.get('pk'))
        pk = self.kwargs.get('pk')
        trip = Trip.objects.get(pk=pk)
        trip_no = trip.dispatch_no
        delivery_boy = trip.delivery_boy
        trip_date = trip.created_at
        no_of_orders = trip.rt_invoice_trip.all().count()
        amount = 0
        invoices = trip.rt_invoice_trip.all()
        trip_detail_list =[]
        for invoice in invoices:
            products=[]
            amount += float(invoice.invoice_amount)
            for n in invoice.rt_order_product_order_product_mapping.all():
                products.append(n.product)
            no_of_products = len(list(set(products)))
            trip_invoice_details = {
                        "invoice_no":  invoice.invoice_no,
                        "retailer_address": invoice.shipment_address,
                        "no_of_products": no_of_products,
                        "invoice_amount": invoice.invoice_amount

            }
            trip_detail_list.append(trip_invoice_details)
        total_invoice_amount = round(amount, 2)
        data = {
            "object": trip_obj,
            "trip": trip,
            "trip_no": trip_no,
            "delivery_boy": delivery_boy,
            "trip_date": trip_date,
            "no_of_orders": no_of_orders,
            "total_invoice_amount": total_invoice_amount,
            "url": request.get_host(),
            "scheme": request.is_secure() and "https" or "http",
            "trip_detail_list":trip_detail_list

        }

        cmd_option = {
            "margin-top": 10,
            "zoom": 1,
            "javascript-delay": 1000,
            "footer-center": "[page]/[topage]",
            "no-stop-slow-scripts": True,
            "quiet": True
        }
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )
        return response


def commercial_shipment_details(request, pk):
    shipment = OrderedProduct.objects.select_related('order').get(pk=pk)
    shipment_products = OrderedProductMapping.objects.\
        select_related('product').filter(ordered_product=shipment)
    return render(
        request,
        'admin/retailer_to_sp/CommercialShipmentDetails.html',
        {'shipment': shipment, 'shipment_products': shipment_products}
    )


def reshedule_update_shipment(form_instance, formset):
    if form_instance.trip:
        form_instance.shipment_status = OrderedProduct.RESCHEDULED
        form_instance.trip = None
        form_instance.save()
        for inline_form in formset:
            if inline_form.is_valid:
                product = inline_form.save(commit=False)
                product.delivered_qty = 0
                product.save()


class RetailerCart(APIView):
    permission_classes = (AllowAny,)
    def get(self, request, *args, **kwargs):
        order_obj = Order.objects.get(order_no=request.GET.get('order_no'))
        dt = OrderedCartSerializer(
            order_obj.ordered_cart,
            context={'parent_mapping_id': order_obj.seller_shop.id,}
        )
        return Response({'is_success': True,'response_data': dt.data}, status=status.HTTP_200_OK)


class OrderCancellation(object):
    def __init__(self, instance):
        super(OrderCancellation, self).__init__()
        self.order = instance
        self.order_status = instance.order_status
        self.order_shipments_count = instance.rt_order_order_product.count()
        if self.order_shipments_count:
            self.last_shipment = list(self.get_shipment_queryset())[-1]
            self.shipments_id_list = [i['id'] for i in self.get_shipment_queryset()]
            self.last_shipment_status = self.last_shipment.get('shipment_status')
            self.trip_status = self.last_shipment.get('trip__trip_status')
            self.last_shipment_id = self.last_shipment.get('id')
            self.seller_shop_id = self.last_shipment.get('order__seller_shop__id')
            self.cart = self.last_shipment.get('order__ordered_cart_id')
        else:
            self.cart = instance.ordered_cart

    def get_shipment_queryset(self):
        q = self.order.rt_order_order_product.values(
            'id', 'shipment_status', 'trip__trip_status',
            'order__seller_shop__id', 'order__ordered_cart_id')
        return q

    def get_shipment_products(self, shipment_id_list):
        shipment_products = OrderedProductMapping.objects \
            .values('product_id') \
            .filter(ordered_product_id__in=shipment_id_list)
        return [i['product_id'] for i in shipment_products]

    def get_reserved_qty(self):
        reserved_qty_queryset = OrderedProductReserved.objects \
            .values(sp_grn=F('order_product_reserved_id'),
                    r_qty=F('reserved_qty'), s_qty=F('shipped_qty'),
                    r_product=F('product_id'),
                    man_date=F('order_product_reserved__manufacture_date'),
                    exp_date=F('order_product_reserved__expiry_date'))\
            .filter(cart_id=self.cart)
        return reserved_qty_queryset

    def get_cart_products_price(self, products_list):
        cart_products_price = CartProductMapping.objects \
            .values(product_id=F('cart_product'),
                    product_price=F('cart_product_price__price_to_retailer'))\
            .filter(cart_product_id__in=products_list,
                    cart=self.cart)
        product_price_map = {i['product_id']: i['product_price']
                             for i in cart_products_price}

        return product_price_map

    def generate_credit_note(self, order_closed):
        address_id = Address.objects \
            .values('id') \
            .filter(shop_name_id=self.seller_shop_id) \
            .last().get('id')
        # creating note id
        note_id = brand_credit_note_pattern(Note, 'credit_note_id',
                                            None, address_id)

        credit_amount = 0

        credit_note = Note.objects.create(shop_id=self.seller_shop_id,
                                          credit_note_id=note_id,
                                          shipment_id=self.last_shipment_id,
                                          amount=0, status=True)
        # creating SP GRN
        credit_grn = SPOrderedProduct.objects.create(credit_note=credit_note)

        shipment_products = self.get_shipment_products([self.last_shipment_id])
        product_price_map = self.get_cart_products_price(shipment_products)

        reserved_qty_queryset = self.get_reserved_qty()

        # Creating SP GRN products
        if order_closed:
            for item in reserved_qty_queryset:
                SPOrderedProductMapping.objects.create(
                    shop_id=self.seller_shop_id, ordered_product=credit_grn,
                    product_id=item['r_product'],
                    shipped_qty=item['s_qty'],
                    available_qty=item['s_qty'],
                    damaged_qty=0,
                    ordered_qty=item['s_qty'],
                    delivered_qty=item['s_qty'],
                    manufacture_date=item['man_date'],
                    expiry_date=item['exp_date'],
                )
                product_price = product_price_map[item['r_product']]
                product_price = float(round(product_price, 2))
                credit_amount += (int(item['s_qty']) *
                                  product_price)
        else:
            for item in reserved_qty_queryset:
                SPOrderedProductMapping.objects.create(
                    shop_id=self.seller_shop_id, ordered_product=credit_grn,
                    product_id=item['r_product'],
                    shipped_qty=item['r_qty'],
                    available_qty=item['r_qty'],
                    damaged_qty=0,
                    ordered_qty=item['r_qty'],
                    delivered_qty=item['r_qty'],
                    manufacture_date=item['man_date'],
                    expiry_date=item['exp_date'],
                )
                product_price = product_price_map[item['r_product']]
                product_price = float(round(product_price, 2))
                credit_amount += (int(item['s_qty']) *
                                  product_price)

        # update credit note amount
        credit_note.amount = credit_amount
        credit_note.save()
        reserved_qty_queryset.update(reserve_status=OrderedProductReserved.ORDER_CANCELLED)

    def update_sp_qty_from_cart_or_shipment(self):

        reserved_qty_queryset = self.get_reserved_qty()

        for item in reserved_qty_queryset:
            SPOrderedProductMapping.objects\
                .filter(id=item['sp_grn'])\
                .update(available_qty=(F('available_qty') + item['r_qty']))

        reserved_qty_queryset.update(reserve_status=OrderedProductReserved.ORDER_CANCELLED)

    def cancel(self):
        # check if order associated with any shipment

        # if there is only one shipment for an order
        if self.order_shipments_count == 1:

            # if shipment created but invoice is not generated
            # directly add items to inventory
            if (self.last_shipment_status == 'SHIPMENT_CREATED' and
                    not self.trip_status):
                self.update_sp_qty_from_cart_or_shipment()
                self.get_shipment_queryset().update(shipment_status='CANCELLED')

            # if invoice created but shipment is not added to trip
            # cancel order and generate credit note
            elif (self.last_shipment_status == 'READY_TO_SHIP' and
                    not self.trip_status):
                self.generate_credit_note(order_closed=self.order.order_closed)
                # updating shipment status
                self.get_shipment_queryset().update(shipment_status='CANCELLED')

            elif self.trip_status and self.trip_status == 'READY':
                # cancel order and generate credit note and
                # remove shipment from trip
                self.generate_credit_note(order_closed=self.order.order_closed)
                # updating shipment status and remove trip
                self.get_shipment_queryset().update(
                    shipment_status='CANCELLED', trip=None)
            else:
                # can't cancel the order
                pass
        # if there are more than one shipment for an order
        elif (self.order_shipments_count > 1):
            shipments_status = set([x.get('shipment_status')
                                    for x in self.get_shipment_queryset()])
            shipments_status_count = len(shipments_status)
            if (shipments_status_count == 1 and
                    list(shipments_status)[-1] == 'SHIPMENT_CREATED'):
                self.update_sp_qty_from_cart_or_shipment()
                self.get_shipment_queryset().update(shipment_status='CANCELLED')
            else:
                # can't cancel the order if user have more than one shipment
                pass
        # if there is no shipment for an order
        else:
            # get cart products list
            self.update_sp_qty_from_cart_or_shipment()
            # when there is no shipment created for this order
            # cancel the order


@receiver(post_save, sender=Order)
def order_cancellation(sender, instance=None, created=False, **kwargs):
    if instance.order_status == 'CANCELLED':
        order = OrderCancellation(instance)
        order.cancel()

class StatusChangedAfterAmountCollected(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)


    def post(self, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        cash_collected = self.request.POST.get('cash_collected')
        shipment = OrderedProduct.objects.get(id=shipment_id)
        if float(cash_collected) == float(shipment.cash_to_be_collected()):
            update_order_status(
                close_order_checked=False,
                shipment_id=shipment_id
            )
            msg = {'is_success': True, 'message': ['Status Changed'], 'response_data': None}
        else:
            msg = {'is_success': False, 'message': ['Amount is different'], 'response_data': None}
        return Response(msg, status=status.HTTP_201_CREATED)
