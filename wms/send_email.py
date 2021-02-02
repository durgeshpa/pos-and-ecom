import logging
info_logger = logging.getLogger('file-info')
from global_config.models import GlobalConfig

from django.core.mail import EmailMessage


def send_mail_w_attachment(response, responses):

    try:
        email = EmailMessage()
        email.subject = 'To be Expired Products'
        email.body = 'Products expiring in next 7 days or less'
        sender = GlobalConfig.objects.get(key='sender')
        email.from_email = sender.value
        receiver = GlobalConfig.objects.get(key='recipient')
        email.to = [receiver.value]
        email.attach('Expired_Products.xlsx', responses.getvalue(), 'application/ms-excel')
        email.attach('To_be_Expired_Products.xlsx', response.getvalue(), 'application/ms-excel')
        email.send()

    except Exception as e:
        info_logger.error(e)
