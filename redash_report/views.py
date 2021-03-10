from datetime import datetime
from datetime import date
from django.http import HttpResponse

from .mail_conf import send_mail
from .models import RedashScheduledReport

import logging
info_logger = logging.getLogger('file-info')


def redash_scheduled_report():
    today = datetime.now()
    week_day = today.strftime('%A')
    month_date = str(date.today().day)
    info_logger.info('redash_scheduled_report_cron started at {}'.format(datetime.now()))
    reports = RedashScheduledReport.objects.all()

    for report in reports:
        # check for daily scheduled report
        if report.schedule == "Daily":
            send_mail(report)
            info_logger.info('redash_scheduled_report_cron | Report sent for Daily Scheduled Report at {}'.format(datetime.now()))

        # for weekly scheduled report checking day
        elif report.schedule == week_day:
            send_mail(report)
            info_logger.info('redash_scheduled_report_cron | Report sent for Weekly Scheduled Report at {}'.format(datetime.now()))

        # for monthly scheduled report checking month
        elif report.schedule == month_date:
            send_mail(report)
            info_logger.info('redash_scheduled_report_cron | Report sent for Monthly Scheduled Report at '.format(datetime.now()))

    info_logger.info('redash_scheduled_report_cron ended at {}'.format(datetime.now()))
    return HttpResponse("Done")


