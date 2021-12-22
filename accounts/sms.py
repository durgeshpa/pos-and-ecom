import urllib.parse
import requests, re
from decouple import config
from django.core.exceptions import ValidationError

class SendSms(object):
    """Configure to change SMS backend"""
    def __init__(self, phone,mask='GRAMFAC'):
        super(SendSms, self).__init__()
        self.phone = phone
        self.mask = mask

    def validate_mobile(self):
        rule = re.compile(r'^[6-9]\d{9}$')
        phone = self.phone
        if not rule.search(phone):
            error = u"Please enter a valid mobile number"
            raise ValidationError(error)

    def send(self, body):
        phone = self.phone
        message = urllib.parse.quote_plus(body)
        self.validate_mobile()
        try:
            query = {
                'sender': 'GFctry',
                'route': '4',
                'mobiles': phone,
                'authkey': config('SMS_AUTH_KEY'),
                'country': '91',
                'message':message,
                'mask' : self.mask
                }
            req = requests.get('http://api.msg91.com/api/sendhttp.php', params=query)
            return req.status_code
        except:
            if not self.fail_silently:
                raise
