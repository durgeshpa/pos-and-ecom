# -*- coding: utf-8 -*-

from calendar import weekday
import re
import time
from django.db.models import query
import requests
import logging
from datetime import date, datetime, timedelta

from io import BytesIO

from django.core.files.base import ContentFile
import requests

from celery.task import task
from celery.utils.log import get_task_logger

from report.utils import return_host_report_operators, return_redash_query_no_and_key
from report.models import AsyncReportRequest, ScheduledReport
from global_config.models import GlobalConfig
from retailer_backend.common_function import send_mail

logger = logging.getLogger('report_task')
celery_logger = get_task_logger(__name__)

@task
def HostReportGenerator(rid, extra_params=None):
    try:
        report = AsyncReportRequest.objects.get(id=rid)
        generator_fnc, model = return_host_report_operators(report.report_name)
        params = report.input_params
        queryset = model.objects.filter(**params)
        try:
            response = generator_fnc(queryset)
            file_name = "{}.csv".format(report.rid)
            report.report.save(file_name, BytesIO(response.content), save=False)
            AsyncReportRequest.objects.filter(id=rid).update(status='S',
                                                            report=report.report, 
                                                            report_created_at=datetime.now())
            mail_report.delay(rid)
        except Exception as exp:
            AsyncReportRequest.objects.filter(id=rid).update(status='F')
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except AsyncReportRequest.DoesNotExist:
        logger.info("Async report entry does not exist with ID {}".format(rid))
        celery_logger.exception("Async report entry does not exist with ID {}".format(rid))

@task
def RedashReportGenerator(rid, extra_params=None):
    try:
        report = AsyncReportRequest.objects.get(id=rid)
        try:
            query_no, api_key = return_redash_query_no_and_key(report.report_name)
            #('336','CnT3JxUSvHeoNWA90G7baIJaRt1j4NazmKA4D0Mu')
            #
            URL = "https://redash.gramfactory.com/api/queries/{}/results.csv?api_key={}".format(query_no, api_key)
            with requests.Session() as s:
                try:
                    response = s.post(URL, json=report.input_params)
                    print(response, URL, report.input_params)
                    file_name = "{}.csv".format(report.rid)
                    report.report.save(file_name, BytesIO(response.content), save=False)
                    AsyncReportRequest.objects.filter(id=rid).update(status='S',
                                                                report=report.report, 
                                                                report_created_at=datetime.now())
                    mail_report.delay(rid)
                except Exception as exp:
                    AsyncReportRequest.objects.filter(id=rid).update(status='F')
                    logger.exception("Report generation failed due to {}".format(exp))
                    celery_logger.exception("Report generation failed due to {}".format(exp))
        except KeyError as exp:
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except AsyncReportRequest.DoesNotExist:
        logger.info("Async report entry does not exist with ID {}".format(rid))
        celery_logger.exception("Async report entry does not exist with ID {}".format(rid))

@task
def ScheduledHostReportGenerator(rid, date_params=None):
    try:
        report = AsyncReportRequest.objects.get(id=rid)
        generator_fnc, model = return_host_report_operators(report.report_name)
        params = report.input_params
        if date_params:
            params['created_at__date__gte'] = date_params['date_start']
        else:
            pass
        queryset = model.objects.filter(**params)
        try:
            response = generator_fnc(queryset)
            file_name = "{}.csv".format(report.rid)
            report.report.save(file_name, BytesIO(response.content), save=False)
            AsyncReportRequest.objects.filter(id=rid).update(status='S',
                                                        report=report.report, 
                                                        report_created_at=datetime.now())
            ScheduledReport.objects.create(request=report, report=report.report)
            mail_report.delay(rid)
        except Exception as exp:
            AsyncReportRequest.objects.filter(id=rid).update(status='F')
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except AsyncReportRequest.DoesNotExist:
        logger.info("Async report entry does not exist with ID {}".format(rid))
        celery_logger.exception("Async report entry does not exist with ID {}".format(rid))

@task
def ScheduledRedashReportGenerator(rid, date_params=None):
    pass

@task
def daily_reports():
    reports = AsyncReportRequest.objects.filter(frequency='Daily', 
                                                report_type='SC', 
                                                schedule_time__range=(datetime.now().time, 
                                                                      (datetime.now() + timedelta(minutes=1)).time))
    params = {}
    for report in reports:
        if report.source == 'HT':
            params['date_start'] = datetime.now() - timedelta(days=1)
            ScheduledHostReportGenerator.delay(report.id, params)
        else:
            ScheduledRedashReportGenerator.delay(report.id, params)

@task
def weekly_reports():
    weekday = datetime.today().strftime('%A')
    reports = AsyncReportRequest.objects.filter(frequency=weekday, 
                                                report_type='SC', 
                                                schedule_time__range=(datetime.now().time, 
                                                                      (datetime.now() + timedelta(minutes=1)).time))
    params = {}
    for report in reports:
        if report.source == 'HT':
            params['date_start'] = datetime.now() - timedelta(days=7)
            ScheduledHostReportGenerator.delay(report.id, params)
        else:
            ScheduledRedashReportGenerator.delay(report.id, params)

@task
def monthly_reports():
    monthday = datetime.today().strftime("%d")
    reports = AsyncReportRequest.objects.filter(frequency=monthday, 
                                                report_type='SC',
                                                schedule_time__range=(datetime.now().time, 
                                                                      (datetime.now() + timedelta(minutes=1)).time))
    params = {}
    for report in reports:
        if report.source == 'HT':
            params['date_start'] = datetime.now() - timedelta(days=30)
            ScheduledHostReportGenerator.delay(report.id, params)
        else:
            ScheduledRedashReportGenerator.delay(report.id, params)    

@task
def mail_report(rid):
    try:
        report = AsyncReportRequest.objects.get(id=rid)
        with requests.Session() as s:
            response = s.get(report.report.url)
            report_file = response.content
            report_name = {
                entry[0]: entry[1]    
                for entry in AsyncReportRequest.REPORT_CHOICE
            }
            if report.report_type == 'AD':
                subject = "Report | {}".format(report_name.get(report.report_name))
            else:
                weekly = map(lambda t : t[0], filter(lambda a : a == 'Weekly', AsyncReportRequest.FREQUENCY_CHOICES))
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
    except AsyncReportRequest.DoesNotExist:
        logger.info("Async report entry does not exist with ID {}".format(rid))
        celery_logger.exception("Async report entry does not exist with ID {}".format(rid))
