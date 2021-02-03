import logging
info_logger = logging.getLogger('file-info')
from global_config.models import GlobalConfig

from django.core.mail import EmailMessage


def send_mail_w_attachment(response, responses, warehouse_id,warehouse_name):

    subject = 'To be Expired Products | {} - {}'.format(warehouse_name,warehouse_id)
    expired_products = 'Expired_Products_{}.xlsx'.format(warehouse_id)
    to_be_expired_products = 'To_be_Expired_Products_{}.xlsx'.format(warehouse_id)

    try:
        email = EmailMessage()
        email.subject = subject
        email.body = 'Products expiring in next 7 days or less'
        sender = GlobalConfig.objects.get(key='sender')
        email.from_email = sender.value
        receiver = GlobalConfig.objects.get(key='recipient')
        email.to = eval(receiver.value)
        email.attach(expired_products, responses.getvalue(), 'application/ms-excel')
        email.attach(to_be_expired_products, response.getvalue(), 'application/ms-excel')
        email.send()
    except Exception as e:
        info_logger.error(e)
