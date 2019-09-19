from dal import autocomplete
from django.shortcuts import render

from retailer_to_sp.models import Order
from .models import Payment

# Create your views here.


class OrderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Order.objects.all()#filter(Order_parent__isnull=True,active_status='active')
        if self.q:
            qs = qs.filter(order_no__icontains=self.q)
        return qs


class OrderPaymentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        import pdb; pdb.set_trace()
        qs = Payment.objects.all()

        order = self.forwarded.get('order', None)

        if order:
            users = order.buyer_shop.related_users.all()
            qs = qs.filter(paid_by=users)

        if self.q:
            qs = qs.filter(Q(buyer_shop__shop_owner__phone_number__icontains=self.q) | Q(buyer_shop__shop_name__icontains=self.q))

        return qs