import csv
import codecs
import datetime
import os
import logging

from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View

from accounts.models import User
from .forms import (
	GroupNotificationForm
    )

logger = logging.getLogger(__name__)


# Create your views here.


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