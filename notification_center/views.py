import csv
import codecs
import datetime
import os
import logging

from dal import autocomplete
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View

from accounts.models import User
from shops.models import Shop
from .forms import (
	GroupNotificationForm
    )

logger = logging.getLogger(__name__)


# Create your views here.
class CityAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        buyer_shop = self.forwarded.get('buyer_shop', None)
        state = self.forwarded.get('state', None)
        qs = City.objects.all()
        if buyer_shop:
            qs = qs.filter(city_address__shop_name_id=buyer_shop,
                           city_address__address_type='shipping')
        if state:
            qs = qs.filter(state=state)
        if self.q:
            qs = qs.filter(city_name__icontains=self.q)
        return qs


class SellerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Shop.objects.filter(shop_type__shop_type='sp')
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs



class BuyersAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Shop.objects.filter(shop_type__shop_type='sp')
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class RetailerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        city = self.forwarded.get('city', None)
        pincode_from = self.forwarded.get('pincode_from', None)
        pincode_to = self.forwarded.get('pincode_to', None)

        qs = Shop.objects.filter(shop_type__shop_type='r')

        address = Address.objects.all()
        if city:
            address = address.filter(city=city)
        if pincode_from and pincode_to:
            address = address.filter(pincode__range=(pincode_from, pincode_to))
        #find shop for the address
        shops = address.values('shop_name')
        qs = qs.filter(pk__in=shops)

        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class PincodeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        city = self.forwarded.get('city', None)
        buyer_shop = self.forwarded.get('buyer_shop', None)
        qs = Pincode.objects.all()
        if buyer_shop:
            qs = qs.filter(pincode_address__shop_name_id=buyer_shop,
                           pincode_address__address_type='shipping')
            return qs
        if city:
            qs = qs.filter(city_id=city)
        return qs


def fetch_user_data(user_id):
	# This function will fetch user data from user_id

	user = User.objects.get(id=user_id)
	user_data = {}
	user_data['first_name'] = user.first_name
	user_data['phone_number'] = user.phone_number

	return user_data


def group_notification_view(request):
    """Returns CSV includes products of specific category and brand

    :param request: Form
    :return: Products CSV for selected Category and Brands
    """
    if request.method == 'POST':
        form = GroupNotificationForm(request.POST, request.FILES)

        if form.errors:
            return render(
                request,
                'admin/notification_center/group_notification_scheduler/group-notification.html',
                {'filter_form': form}
            )
        if form.is_valid():
        	pass
    else:
        form = GroupNotificationForm()
    return render(
        request,
        'admin/notification_center/group_notification_scheduler/group-notification.html',
        {'filter_form': form}
    )