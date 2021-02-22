import logging
info_logger = logging.getLogger('file-info')

from global_config.models import GlobalConfig
from django.core.mail import EmailMessage
import urllib.request


def send_mail(data):
    info_logger.info("redash_scheduled_report_cron | Send Email Function started")
    body = data.body
    subject = data.subject
    url = data.csv_url
    response = urllib.request.urlopen(url).read()
    recipient_list = data.recipients
    recipients = recipient_list.split(",")
    try:
        email = EmailMessage()
        email.subject = subject
        email.body = body
        sender = GlobalConfig.objects.get(key='sender')
        email.from_email = sender.value
        email.to = recipients
        email.attach('result.csv', response, 'application/csv')
        email.send()
        info_logger.info("redash_scheduled_report_cron | Email Successfully Sent")
    except Exception as e:
        info_logger.error("redash_scheduled_report_cron | ", e)
