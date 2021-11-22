import datetime
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apis.users.models import UserDetail


'''
	Management command to receive status of pending payments from Bharatpe
'''
class Command(BaseCommand):
	def handle(self, *args, **options):
		today = datetime.datetime.now().date()
		pending_payments = Payment.objects.filter(Q(payment_mode_name="credit_payment") & Q(is_payment_approved=False))

        try:
            headers = {'Content-Type': 'application/json', 
	            'Accept':'application/json',
	            'hash': convert_hash_using_hmac_sha256(payload)}

        	for payment in pending_payments:
        		payload = {}
        		payload['payment_id'] = payment.payment_id
	            resp = requests.get(BHARATPE_BASE_URL+"/payment-callback-url", data = json.dumps(payload), headers=headers)        
	            data = json.loads(resp.content)         
	            payment.is_payment_approved = data['payment_status']
	            payment.save()

        except Exception as e:
            logging.info("Class name: %s - Error = %s:"%('Bharatpe',str(e)))
            logging.info(traceback.format_exc(sys.exc_info()))