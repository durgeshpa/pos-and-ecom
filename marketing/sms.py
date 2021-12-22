import re
from decouple import config

from django.core.exceptions import ValidationError

from .tasks import send_gupshup_request


class SendSms(object):
    """Configure to change SMS backend"""

    def __init__(self, phone, body,mask="GRAMFAC"):
        super(SendSms, self).__init__()
        self.phone = phone
        self.body = body
        self.mask = mask

    def send(self):
        message = self.body
        number = ValidatePhone(self.phone)
        number.validate_mobile()
        try:
            query = {
                'method': 'SendMessage',
                'send_to': '91%s' % self.phone,
                'msg': message,
                'userid': config('SMS_USER_ID'),
                'auth_scheme': 'plain',
                'password': config('SMS_PWD'),
                'v': '1.1',
                'format': 'text',
                'mask':self.mask

            }
            url = "https://enterprise.smsgupshup.com/GatewayAPI/rest"
            return send_gupshup_request.delay(url, query)
        except:
            error, status_code = "Something went wrong! Please try again", "400"
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
            raise ValidationError(u"Please enter a valid mobile number")
