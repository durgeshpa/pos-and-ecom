from django.shortcuts import render
from .forms import RedashForm

import logging
info_logger = logging.getLogger('file-info')
from global_config.models import GlobalConfig
from django.core.mail import EmailMessage
import urllib.request


def scheduled_report(request):
    context = {'form': RedashForm()}
    if request.POST:
        url = request.POST['csv_url']
        response = urllib.request.urlopen(url).read()
        recipient = request.POST['recipient']
        subject = request.POST['subject']
        body = request.POST['body']
        ScheduledMail(response, recipient, subject, body)
    return render(request, "admin/redash_report/redash.html", context)


# schedule_email_notification(schedule=date, repeat=Task.DAILY)
def ScheduledMail(response, recipient, subject, body):
    try:
        email = EmailMessage()
        email.subject = subject
        email.body = body
        sender = GlobalConfig.objects.get(key='sender')
        email.from_email = sender.value
        email.to = [recipient]
        email.attach('result.csv', response, 'application/csv')
        email.send()
    except Exception as e:
        info_logger.error(e)