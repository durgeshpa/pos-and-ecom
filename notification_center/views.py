from django.shortcuts import render

from accounts.models import User
# Create your views here.


def fetch_user_data(user_id):
	# This function will fetch user data from user_id

	user = User.objects.get(id=user_id)
	user_data = {}
	user_data['first_name'] = user.first_name
	user_data['phone_number'] = user.phone_number

	return user_data
