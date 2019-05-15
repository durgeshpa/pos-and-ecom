from celery.task import task
from otp.models import PhoneOTP
from rest_framework.authtoken.models import Token


@task
def phone_otp_instance(phone_number, created):
	otp_instance = PhoneOTP.objects.filter(phone_number=phone_number)
	if not otp_instance.exists():
		PhoneOTP.objects.create(phone_number=phone_number)


@task
def create_user_token(user_id):
	Token.objects.create(user_id=user_id)

