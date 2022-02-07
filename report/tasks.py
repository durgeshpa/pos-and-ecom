# -*- coding: utf-8 -*-

import requests
import logging
from datetime import datetime, timedelta

from io import BytesIO
import requests

from celery.task import task
from celery.utils.log import get_task_logger
from report.redash import Redash

from report.utils import (return_host_generator_function, 
                          return_model_ref, 
                          flat_to_nested_dict)
from report.models import ReportChoice, ReportRequest, ScheduledReport
from global_config.models import GlobalConfig
from retailer_backend.common_function import send_mail

logger = logging.getLogger('report_task')
celery_logger = get_task_logger(__name__)

@task
def HostReportGenerator(rid, date_params=None):
    if not date_params:
        date_params = {}
    try:
        report = ReportRequest.objects.get(id=rid)
        input_params = report.input_params
        model = return_model_ref(report.report_choice.target_model)
        generator_fnc = return_host_generator_function(report.report_choice.generator_function)
        default_mappings = report.report_choice.default_mappings
        required_mappings = report.report_choice.required_mappings
        optional_mappings = report.report_choice.optional_mappings
        if default_mappings:
            params = default_mappings
        else:
            params = {}
        if required_mappings:
            for key, mapping in required_mappings.items():
                params[mapping] = date_params.get(key) \
                    if date_params.get(key) else input_params.get(key)
        if optional_mappings:
            for key, mapping in optional_mappings.items():
                if input_params.get(key):
                    params[mapping] = date_params.get(key) \
                        if date_params.get(key) else input_params.get(key)
        queryset = model.objects.filter(**params)
        try:
            response = generator_fnc(queryset)
            file_name = "{}.csv".format(report.rid)
            report.report.save(file_name, BytesIO(response.content), save=False)
            ReportRequest.objects.filter(id=rid).update(status='S',
                                                            report=report.report, 
                                                            report_created_at=datetime.now())
            if report.report_type == 'SC':
                ScheduledReport.objects.create(request=report, report=report.report)
            mail_report.delay(rid)
        except Exception as exp:
            ReportRequest.objects.filter(id=rid).update(status='F', 
                                                        failed_message=exp)
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except ReportRequest.DoesNotExist:
        logger.info(" report entry does not exist with ID {}".format(rid))
        celery_logger.exception(" report entry does not exist with ID {}".format(rid))


@task
def RedashReportGenerator(rid, date_params=None):
    if not date_params:
        date_params = {}
    try:
        report = ReportRequest.objects.get(id=rid)
        try:
            query_no = report.report_choice.query_no
            token = report.report_choice.token
            input_params = report.input_params
            default_mappings = report.report_choice.default_mappings
            required_mappings = report.report_choice.required_mappings
            optional_mappings = report.report_choice.optional_mappings
            if default_mappings:
                params = default_mappings
            else:
                params = {}
            parameters = {}
            if required_mappings:
                for key, value in required_mappings.items():
                    params['parameters.' + value] = date_params.get(key) if date_params.get(key) else input_params.get(key)
            if optional_mappings:
                for key, value in optional_mappings.items():
                    if input_params.get(key):
                        params['parameters.' + value] = date_params.get(key) if date_params.get(key) else input_params.get(key)
            params = flat_to_nested_dict(params)
            redash = Redash(query_no, token, rid)
            response = redash.refresh_query(params)
            file_name = "{}.csv".format(report.rid)
            report.report.save(file_name, BytesIO(response.content), save=False)
            ReportRequest.objects.filter(id=rid).update(status='S',
                                                        report=report.report, 
                                                        report_created_at=datetime.now())
            if report.report_type == 'SC':
                ScheduledReport.objects.create(request=report, report=report.report)
            mail_report.delay(rid)
        except Exception as exp:
            ReportRequest.objects.filter(id=rid).update(status='F', 
                                                        failed_message=exp)
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except ReportRequest.DoesNotExist:
        logger.info(" report entry does not exist with ID {}".format(rid))
        celery_logger.exception(" report entry does not exist with ID {}".format(rid))


@task
def ScheduledHostReportGenerator(rid, date_params=None):
    print("here")
    try:
        report = ReportRequest.objects.get(id=rid)
        input_params = report.input_params
        model = return_model_ref(report.report_choice.target_model)
        generator_fnc = return_host_generator_function(report.report_choice.generator_function)
        default_mappings = report.report_choice.default_mappings
        required_mappings = report.report_choice.required_mappings
        optional_mappings = report.report_choice.optional_mappings
        if default_mappings:
            params = default_mappings
        else:
            params = {}
        if required_mappings:
            for key, mapping in required_mappings.items():
                params[mapping] = input_params.get(key)
        if optional_mappings:
            for key, mapping in optional_mappings.items():
                if input_params.get(key):
                    params[mapping] = input_params.get(key)
        queryset = model.objects.filter(**params)
        if date_params:
            params['created_at__date__gte'] = date_params['date_start']
        else:
            pass
        print(params)
        queryset = model.objects.filter(**params)
        try:
            response = generator_fnc(queryset)
            file_name = "{}.csv".format(report.rid)
            report.report.save(file_name, BytesIO(response.content), save=False)
            ReportRequest.objects.filter(id=rid).update(status='S',
                                                        report=report.report, 
                                                        report_created_at=datetime.now())
            ScheduledReport.objects.create(request=report, report=report.report)
            mail_report.delay(rid)
        except Exception as exp:
            ReportRequest.objects.filter(id=rid).update(status='F')
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except ReportRequest.DoesNotExist:
        logger.info(" report entry does not exist with ID {}".format(rid))
        celery_logger.exception(" report entry does not exist with ID {}".format(rid))

@task
def ScheduledRedashReportGenerator(rid, date_params=None):
    try:
        report = ReportRequest.objects.get(id=rid)
        try:
            params["parameters"] = params
            params["max_age"] = params["max_age"]
            print(params)
            URL = "https://redash.gramfactory.com/api/queries/{}/results.csv?api_key={}".format(query_no, token)
            with requests.Session() as s:
                try:
                    response = s.post(URL, json=params)
                    print(response, URL, params)
                    file_name = "{}.csv".format(report.rid)
                    report.report.save(file_name, BytesIO(response.content), save=False)
                    ReportRequest.objects.filter(id=rid).update(status='S',
                                                                report=report.report, 
                                                                report_created_at=datetime.now())
                    mail_report.delay(rid)
                except Exception as exp:
                    ReportRequest.objects.filter(id=rid).update(status='F')
                    logger.exception("Report generation failed due to {}".format(exp))
                    celery_logger.exception("Report generation failed due to {}".format(exp))
        except KeyError as exp:
            logger.exception("Report generation failed due to {}".format(exp))
            celery_logger.exception("Report generation failed due to {}".format(exp))
    except ReportRequest.DoesNotExist:
        logger.info(" report entry does not exist with ID {}".format(rid))
        celery_logger.exception(" report entry does not exist with ID {}".format(rid))


@task
def daily_reports():
    reports = ReportRequest.objects.filter(frequency='Daily', 
                                                report_type='SC', 
                                                schedule_time__range=(datetime.now().time, 
                                                                      (datetime.now() + timedelta(minutes=1)).time))
    params = {}
    params['date_start'] = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    for report in reports:
        if report.source == 'HT':
            HostReportGenerator.delay(report.id, params)
        else:
            params['date_end'] = datetime.now().strftime("%Y-%m-%d")
            RedashReportGenerator.delay(report.id, params)

@task
def weekly_reports():
    weekday = datetime.today().strftime('%A')
    reports = ReportRequest.objects.filter(frequency=weekday, 
                                                report_type='SC', 
                                                schedule_time__range=(datetime.now().time, 
                                                                      (datetime.now() + timedelta(minutes=1)).time))
    params = {}
    for report in reports:
        if report.source == 'HT':
            params['date_start'] = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            HostReportGenerator.delay(report.id, params)
        else:
            params['date_end'] = datetime.now().strftime("%Y-%m-%d")
            RedashReportGenerator.delay(report.id, params)

@task
def monthly_reports():
    monthday = datetime.today().strftime("%d")
    reports = ReportRequest.objects.filter(frequency=monthday, 
                                                report_type='SC',
                                                schedule_time__range=(datetime.now().time, 
                                                                      (datetime.now() + timedelta(minutes=1)).time))
    params = {}
    for report in reports:
        if report.source == 'HT':
            params['date_start'] = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            HostReportGenerator.delay(report.id, params)
        else:
            params['date_end'] = datetime.now().strftime("%Y-%m-%d")
            RedashReportGenerator.delay(report.id, params)    

@task
def mail_report(rid):
    try:
        report = ReportRequest.objects.get(id=rid)
        with requests.Session() as s:
            response = s.get(report.report.url)
            report_file = response.content
            if report.report_type == 'AD':
                subject = "Report | {}".format(report.report_choice.name)
            else:
                weekly = map(lambda t : t[0], filter(lambda a : a == 'Weekly', ReportRequest.FREQUENCY_CHOICES))
                if report.frequency == "Daily":
                    freq = "Daily"
                elif report.frequency in weekly:
                    freq = "Weekly | {} |".format(report.frequency)
                else:
                    freq = "Monthly"
                subject = "{} Report | {}".format(freq, report.report_choice.name)
            try:
                attachements = [{
                    'name': '{}.csv'.format(report.rid),
                    'value': report_file,
                    'type': 'text/csv'
                }]
                sender = GlobalConfig.objects.filter(key='report_mail_sender').last()
                if not sender:
                    ReportRequest.objects.filter(id=rid).update(status='EF')
                    celery_logger.exception("Please add a sender with key ::: report_mail_sender :::")
                    return
                emails = report.emails + [report.user.email]
                send_mail(sender.value, emails, subject, '', attachements)
            except Exception as err:
                ReportRequest.objects.filter(id=rid).update(status='EF')
                celery_logger.exception("Sending of report over email failed due to {}".format(err))
    except ReportRequest.DoesNotExist:
        logger.info(" report entry does not exist with ID {}".format(rid))
        celery_logger.exception(" report entry does not exist with ID {}".format(rid))
