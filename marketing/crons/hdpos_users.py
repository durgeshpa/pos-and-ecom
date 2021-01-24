import logging
import datetime
import pyodbc
import sys
import os
from django.db import transaction
from decouple import config
from django.utils import timezone
import traceback

from services.models import CronRunLog
from global_config.models import GlobalConfig
from marketing.models import MLMUser, RewardPoint


cron_logger = logging.getLogger('cron_log')
CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST') \
                  + ';DATABASE=' + config('HDPOS_DB_NAME') \
                  + ';UID=' + config('HDPOS_DB_USER') \
                  +';PWD=' + config('HDPOS_DB_PASSWORD')


def fetch_hdpos_users_cron():

    cron_name = CronRunLog.CRON_CHOICE.HDPOS_USERS_FETCH_CRON
    if CronRunLog.objects.filter(cron_name=cron_name, status=CronRunLog.CRON_STATUS_CHOICES.STARTED).exists():
        cron_logger.info("{} already running".format(cron_name))
        return

    cron_log_entry = CronRunLog.objects.create(cron_name=cron_name)
    cron_logger.info("{} started, cron log entry-{}"
                     .format(cron_log_entry.cron_name, cron_log_entry.id))

    try:
        fetch_hdpos_users()
        cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.COMPLETED
        cron_log_entry.completed_at = timezone.now()
        cron_logger.info("{} completed, cron log entry-{}".format(cron_log_entry.cron_name, cron_log_entry.id))

    except Exception as e:
        cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.ABORTED
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        cron_logger.info("{} aborted, cron log entry-{}, {}, {}, {}".format(cron_name, cron_log_entry.id,
                                                                            exc_type, fname, exc_tb.tb_lineno))
        traceback.print_exc()
    cron_log_entry.save()


def fetch_hdpos_users():

    cron_logger.info('hdpos users fetch started')

    date_config = GlobalConfig.objects.filter(key='hdpos_users_fetch').last()

    last_date = ''
    now_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if date_config:
        last_date = date_config.value

    cnxn = pyodbc.connect(CONNECTION_PATH)
    cron_logger.info('connected to hdpos marekting users fetch')
    cursor = cnxn.cursor()

    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir, 'sql/users_sql.sql')
    fd = open(file_path, 'r')
    sqlfile = fd.read()
    fd.close()

    if last_date != '':
        sqlfile = sqlfile + " where customers.RegistrationDate >='" + last_date + "'"

    cursor.execute(sqlfile)

    cron_logger.info('writing hdpos users data')

    with transaction.atomic():

        for row in cursor:

            if not row[0]:
                continue

            row[0] = '' if not row[0] else row[0].replace(' ', '')
            row[1] = '' if not row[1] else row[1].replace(' ', '')
            row[2] = '' if not row[2] else row[2].strip()

            if len(row[0]) != 10:
                continue

            if not MLMUser.objects.filter(phone_number=row[0]).exists():
                user_obj = MLMUser.objects.create(phone_number=row[0], email=row[1], name=row[2])
                RewardPoint.welcome_reward(user_obj, 0)

        if date_config:
            date_config.value = now_date
            date_config.save()
        else:
            GlobalConfig.objects.create(key='hdpos_users_fetch', value=now_date)



