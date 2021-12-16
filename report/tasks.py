# -*- coding: utf-8 -*-

import requests
import logging
from datetime import datetime

from io import BytesIO

from django.core.files.base import ContentFile
import requests

from celery.task import task
from celery.utils.log import get_task_logger

from report.utils import return_report_operators
from report.models import AsyncReport
from global_config.models import GlobalConfig
from retailer_backend.common_function import send_mail

logger = logging.getLogger('report_task')
celery_logger = get_task_logger(__name__)

@task
def ReportGenerator(rid):
    try:
        report = AsyncReport.objects.get(id=rid)
        generator_fnc, model = return_report_operators(report.report_name)
        params = report.input_params
        queryset = model.objects.filter(**params)
        try:
            response = generator_fnc(queryset)
            file_name = "{}.csv".format(report.rid)
            report.report.save(file_name, BytesIO(response.content), save=False)
            AsyncReport.objects.filter(id=rid).update(status='S',
                                                        report=report.report, report_created_at=datetime.now())
            mail_report.delay(rid)
        except Exception as exp:
            AsyncReport.objects.filter(id=rid).update(status='F')
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except AsyncReport.DoesNotExist:
        logger.info("Async report entry does not exist with ID {}".format(rid))
        celery_logger.exception("Async report entry does not exist with ID {}".format(rid))


@task
def mail_report(rid):
    try:
        report = AsyncReport.objects.get(id=rid)
        with requests.Session() as s:
            response = s.get(report.report.url)
            report_file = response.content
            report_name = {
                entry[0]: entry[1]    
                for entry in AsyncReport.REPORT_CHOICE
            }
            if report.report_type == 'AD':
                subject = "Report | {}".format(report_name.get(report.report_name))
            else:
                weekly = map(lambda t : t[0], filter(lambda a : a == 'Weekly', AsyncReport.FREQUENCY_CHOICES))
                if report.frequency == "Daily":
                    freq = "Daily"
                elif report.frequency in weekly:
                    freq = "Weekly | {} |".format(report.frequency)
                else:
                    freq = "Monthly"
                subject = "{} Report | {}".format(freq, report_name.get(report.report_name))
            try:
                attachements = [{
                    'name': '{}.csv'.format(report.rid),
                    'value': report_file,
                    'type': 'text/csv'
                }]
                sender = GlobalConfig.objects.filter(key='report_mail_sender').last()
                if not sender:
                    celery_logger.exception("Please add a sender with key ::: report_mail_sender :::")
                    return
                emails = report.emails + [report.user.email]
                send_mail(sender.value, emails, subject, '', attachements)
            except Exception as err:
                celery_logger.exception("Sending of report over email failed due to {}".format(err))
    except AsyncReport.DoesNotExist:
        logger.info("Async report entry does not exist with ID {}".format(rid))
        celery_logger.exception("Async report entry does not exist with ID {}".format(rid))
