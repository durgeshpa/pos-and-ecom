from celery.task import task
from otp.models import PhoneOTP


@task
def phone_otp_instance(phone_number, created):
	otp_instance = PhoneOTP.objects.filter(phone_number=phone_number)
	if not otp_instance.exists():
		PhoneOTP.objects.create(phone_number=phone_number)

