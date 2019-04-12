from dal import autocomplete
from wkhtmltopdf.views import PDFTemplateResponse

from django.forms import formset_factory, inlineformset_factory, modelformset_factory, BaseFormSet, ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Q


from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from sp_to_gram.models import OrderedProductReserved
from retailer_to_sp.models import (
    Cart, CartProductMapping, Order, OrderedProduct, OrderedProductMapping,
    CustomerCare, Payment, Return, ReturnProductMapping, Note, Trip, Dispatch
)
from products.models import Product
from retailer_to_sp.forms import (
    OrderedProductForm, OrderedProductMappingShipmentForm,
    OrderedProductMappingDeliveryForm, OrderedProductDispatchForm,
    TripForm, DispatchForm, DispatchDisabledForm
)
from django.views.generic import TemplateView
from django.conf import settings

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from retailer_to_sp.api.v1.serializers import DispatchSerializer
import json
from django.http import HttpResponse
from django.core import serializers


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
                                          extra=1, max_num=1, formset=RequiredFormSet
                                          )
    form = OrderedProductForm()
    form_set = ordered_product_set()
    if order_id:
        ordered_product = Cart.objects.filter(pk=order_id)
        ordered_product = Order.objects.get(pk=order_id).ordered_cart
        order_product_mapping = CartProductMapping.objects.filter(
            cart=ordered_product)
        products_list = []
        for item in order_product_mapping.values('cart_product', 'no_of_pieces'):
            already_shipped_qty = OrderedProductMapping.objects.filter(
                ordered_product__in=Order.objects.get(
                    pk=order_id).rt_order_order_product.all(),
                product_id=item['cart_product']).aggregate(
                Sum('delivered_qty')).get('delivered_qty__sum')
            already_shipped_qty = already_shipped_qty if already_shipped_qty else 0

            returned_qty = OrderedProductMapping.objects.filter(
                ordered_product__in=Order.objects.get(
                    pk=order_id).rt_order_order_product.all(),
                product_id=item['cart_product']).aggregate(
                Sum('returned_qty')).get('returned_qty__sum')
            returned_qty = returned_qty if returned_qty else 0

            to_be_shipped_qty = OrderedProductMapping.objects.filter(
                ordered_product__in=Order.objects.get(
                    pk=order_id).rt_order_order_product.all(),
                product_id=item['cart_product']).aggregate(
                Sum('shipped_qty')).get('shipped_qty__sum')
            to_be_shipped_qty = to_be_shipped_qty if to_be_shipped_qty else 0
            to_be_shipped_qty = to_be_shipped_qty - returned_qty

            ordered_no_pieces = item['no_of_pieces']

            if ordered_no_pieces != to_be_shipped_qty + already_shipped_qty:
                products_list.append({
                        'product': item['cart_product'],
                        'ordered_qty': ordered_no_pieces,
                        'already_shipped_qty': already_shipped_qty,
                        'to_be_shipped_qty': to_be_shipped_qty
                        })
        form_set = ordered_product_set(initial=products_list)
        form = OrderedProductForm(initial={'order': order_id})

    if request.method == 'POST':
        form_set = ordered_product_set(request.POST)
        form = OrderedProductForm(request.POST)

        if form.is_valid():
            status = form.cleaned_data.get('shipment_status')
            if status == 'CANCELLED':
                ordered_product_set = formset_factory(OrderedProductMappingShipmentForm,
                                                      extra=1, max_num=1
                                                      )
                form_set = ordered_product_set(request.POST)

            if form_set.is_valid():
                ordered_product_instance = form.save()
                for forms in form_set:
                    if forms.is_valid():
                        to_be_ship_qty = forms.cleaned_data.get('shipped_qty', 0)
                        if to_be_ship_qty:
                            formset_data = forms.save(commit=False)
                            formset_data.ordered_product = ordered_product_instance
                            formset_data.save()
                update_qty = DeductReservedQtyFromShipment(
                    ordered_product_instance, form_set)
                update_qty.update()
                return redirect('/admin/retailer_to_sp/shipment/')

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
                    selected_shipments = Dispatch.objects.filter(
                                                    pk__in=selected_shipments)

                    for shipment_instance in selected_shipments:
                        if current_trip_status == 'READY':
                            shipment_instance.trip = trip
                            shipment_instance.shipment_status = 'READY_TO_DISPATCH'

                        elif shipment_instance.trip == trip and current_trip_status == 'STARTED':
                            shipment_instance.shipment_status = 'OUT_FOR_DELIVERY'

                        elif current_trip_status == 'COMPLETED':
                            ordered_product_mapping = OrderedProductMapping.objects.filter(
                                ordered_product=shipment_instance)
                            for product in ordered_product_mapping:
                                product.delivered_qty = product.shipped_qty
                                product.save()
                            shipment_instance.shipment_status = 'FULLY_DELIVERED_AND_COMPLETED'
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

        vector = SearchVector('order__shipping_address__address_line1')
        query = SearchQuery(area)
        similarity = TrigramSimilarity(
                            'order__shipping_address__address_line1', area)

        if seller_shop and area and trip_id:
            dispatches = Dispatch.objects.annotate(
                            rank=SearchRank(vector, query) + similarity
                            ).filter(
                                Q(shipment_status='READY_TO_SHIP') |
                                Q(trip=trip_id), order__seller_shop=seller_shop
                                ).order_by('-rank')

        elif seller_shop and trip_id:
            dispatches = Dispatch.objects.filter(
                            Q(shipment_status='READY_TO_SHIP') |
                            Q(trip=trip_id), order__seller_shop=seller_shop)

        elif trip_id:
            dispatches = Dispatch.objects.filter(
                                trip=trip_id)

        elif seller_shop and area:
            dispatches = Dispatch.objects.annotate(
                            rank=SearchRank(vector, query) + similarity
                        ).filter(
                            shipment_status='READY_TO_SHIP',
                            order__seller_shop=seller_shop).order_by('-rank')

        elif seller_shop:
            dispatches = Dispatch.objects.select_related('order', 'order__shipping_address', 'order__ordered_cart').filter(
                                            shipment_status='READY_TO_SHIP',
                                            order__seller_shop=seller_shop).order_by('invoice_no')

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

        if dispatches:
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
            "buyer_address":order_obj.ordered_cart.buyer_shop.shop_name_address_mapping.last().address_line1,
            "buyer_city":order_obj.ordered_cart.buyer_shop.shop_name_address_mapping.last().city.city_name,
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


def update_shipment_status(form, formsets):
    form_instance = getattr(form, 'instance', None)
    shipped_qty_list = []
    returned_qty_list = []
    damaged_qty_list = []

    for inline_forms in formsets:
        for inline_form in inline_forms:
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


def update_order_status(form):
    form_instance = getattr(form, 'instance', None)
    total_delivered_qty = []
    total_shipped_qty = []
    total_returned_qty = []
    total_damaged_qty = []
    current_order_shipment = form_instance.order.rt_order_order_product.all()
    for shipment in current_order_shipment:
        shipment_product = shipment.rt_order_product_order_product_mapping.all()
        ordered_qty = sum([int(i.ordered_qty) for i in shipment_product])
        delivered_qty = shipment_product.aggregate(Sum('delivered_qty')).get('delivered_qty__sum', 0)
        shipped_qty = shipment_product.aggregate(Sum('shipped_qty')).get('shipped_qty__sum', 0)
        returned_qty = shipment_product.aggregate(Sum('returned_qty')).get('returned_qty__sum', 0)
        damaged_qty = shipment_product.aggregate(Sum('damaged_qty')).get('damaged_qty__sum', 0)

        total_delivered_qty.append(delivered_qty)
        total_shipped_qty.append(shipped_qty)
        total_returned_qty.append(returned_qty)
        total_damaged_qty.append(damaged_qty)

    order = form_instance.order
    if ordered_qty == (sum(total_delivered_qty) + sum(total_returned_qty) + sum(total_damaged_qty)):
        order.order_status = 'SHIPPED'

    elif (sum(total_returned_qty) == sum(total_shipped_qty) or
          (sum(total_damaged_qty) + sum(total_returned_qty)) == sum(total_shipped_qty)):
        order.order_status = 'DENIED'

    elif (sum(total_delivered_qty) == 0 and sum(total_shipped_qty) > 0 and
            sum(total_returned_qty) == 0 and sum(total_damaged_qty) == 0):
        order.order_status = 'DISPATCH_PENDING'

    elif (ordered_qty - sum(total_delivered_qty)) > 0 and sum(total_delivered_qty) > 0:
        order.order_status = 'PARTIALLY_SHIPPED'
    order.save()


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
            cart=cart, product=product).last()

    def deduct_reserved_qty(self, product, ordered_qty, already_shipped_qty):
        ordered_product_reserved = self.get_sp_ordered_product_reserved(
            product)
        ordered_product_reserved.reserved_qty = (ordered_qty - already_shipped_qty)
        ordered_product_reserved.save()

    def update(self):
        for form in self.shipment_products:
            product = form.instance.product
            already_shipped_qty = form.instance.to_be_shipped_qty
            ordered_qty = int(form.instance.ordered_qty)
            self.deduct_reserved_qty(product, ordered_qty, already_shipped_qty)


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
            cart=cart, product=product).last()

    def get_shipment_status(self):
        shipment_status = self.shipment.instance.shipment_status
        return shipment_status

    def update_shipment_status(self):
        self.shipment.instance.shipment_status = self.shipment.instance.CLOSED
        self.shipment.instance.save()

    def close_order(self):
        status = self.shipment.cleaned_data.get('close_order')
        return status

    def get_reserved_qty(self, product):
        ordered_product_reserved = self.get_sp_ordered_product_reserved(
            product)
        reserved_qty = ordered_product_reserved.reserved_qty
        ordered_product_reserved.reserved_qty = 0
        ordered_product_reserved.save()
        return reserved_qty

    def update_order_status(self):
        self.shipment.instance.order.order_status = self.shipment.instance.\
            order.PARTIALLY_SHIPPED_AND_CLOSED
        self.shipment.instance.order.save()

    def update_available_qty(self, product):
        ordered_product_reserved = self.get_sp_ordered_product_reserved(
            product)
        shipment_product = ordered_product_reserved.order_product_reserved
        shipment_product.available_qty += self.get_reserved_qty(product)
        shipment_product.save()

    def update(self):
        for inline_form in self.shipment_products:
            for form in inline_form:
                product = form.instance.product
                if (
                    self.close_order() and
                    (self.get_shipment_status() !=
                     self.shipment.instance.CLOSED)):

                    self.update_shipment_status()
                    self.update_order_status()
                    self.update_available_qty(product)
