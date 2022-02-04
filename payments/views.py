from dal import autocomplete
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q

from retailer_to_sp.models import Order
from .models import Payment, OrderPayment
from accounts.models import UserWithName
# Create your views here.


class OrderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Order.objects.all()#filter(Order_parent__isnull=True,active_status='active')
        if self.q:
            qs = qs.filter(order_no__icontains=self.q)
        return qs


class OrderPaymentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Payment.objects.all()
        order_id = self.forwarded.get('order', None)

        if order_id:
            order = Order.objects.get(pk=order_id)
            users = order.buyer_shop.related_users.all()
            shop_owner = order.buyer_shop.shop_owner
            qs = qs.filter(Q(paid_by__in=users) | Q(paid_by=shop_owner))

        if self.q:
            qs = qs.filter(Q(buyer_shop__shop_owner__phone_number__icontains=self.q) | Q(buyer_shop__shop_name__icontains=self.q))
        #print (order_id, order, users, shop_owner, qs)
        return qs


class UserWithNameAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = UserWithName.objects.all()
        if self.q:
            qs = qs.filter(Q(phone_number__icontains=self.q) | Q(first_name__icontains=self.q))
        return qs


def GetOrderPaymentAmount(request, order_payment):
    order_amount = OrderPayment.objects.filter(id=order_payment).last().paid_amount
    return JsonResponse({"data": order_amount})
