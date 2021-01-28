import urllib.parse
import re
from decouple import config
from django.core.exceptions import ValidationError
from .tasks import send_gupshup_request


class SendSms(object):
    """Configure to change SMS backend"""

    def __init__(self, phone, body):
        super(SendSms, self).__init__()

        self.phone = phone
        self.body = body

    def send(self):
        """To send SMS"""
        message = self.body
        #    message = urllib.parse.quote_plus(self.body)
        number = ValidatePhone(self.phone)
        number.validate_mobile()
        try:
            query = {
                'method': 'SendMessage',
                'send_to': '91%s' % (self.phone),
                'msg': message,
                'userid': config('SMS_USER_ID'),
                'auth_scheme': 'plain',
                'password': config('SMS_PWD'),
                'v': '1.1',
                'format': 'text'
            }
            url = "https://enterprise.smsgupshup.com/GatewayAPI/rest"
            return send_gupshup_request.delay(url, query)
        except:
            error = "Something went wrong! Please try again"
            status_code = "400"
            return status_code, error


class ValidatePhone(object):
    """To check if number is valid"""

    def __init__(self, phone):
        super(ValidatePhone, self).__init__()
        self.phone = phone

    def validate_mobile(self):
        rule = re.compile(r'^[6-9]\d{9}$')
        phone = self.phone
        if not rule.search(str(phone)):
            error = u"Please enter a valid mobile number"
            raise ValidationError(error)
