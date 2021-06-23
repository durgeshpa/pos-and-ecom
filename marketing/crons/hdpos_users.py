import logging
import datetime
import pyodbc
import sys
import os
import traceback
import re
from decouple import config

from django.db import transaction
from django.utils import timezone

from services.models import CronRunLog
from global_config.models import GlobalConfig
from accounts.models import User

from marketing.models import RewardPoint, ReferralCode, Profile
from franchise.models import ShopLocationMap
from pos.common_functions import create_user_shop_mapping


cron_logger = logging.getLogger('cron_log')
CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST') \
                  + ';DATABASE=' + config('HDPOS_DB_NAME') \
                  + ';UID=' + config('HDPOS_DB_USER') \
                  + ';PWD=' + config('HDPOS_DB_PASSWORD')


def fetch_hdpos_users_cron():
    return
#
#     cron_name = CronRunLog.CRON_CHOICE.HDPOS_USERS_FETCH_CRON
#     if CronRunLog.objects.filter(cron_name=cron_name, status=CronRunLog.CRON_STATUS_CHOICES.STARTED).exists():
#         cron_logger.info("{} already running".format(cron_name))
#         return
#
#     cron_log_entry = CronRunLog.objects.create(cron_name=cron_name)
#     cron_logger.info("{} started, cron log entry-{}"
#                      .format(cron_log_entry.cron_name, cron_log_entry.id))
#
#     try:
#         fetch_hdpos_users()
#         cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.COMPLETED
#         cron_log_entry.completed_at = timezone.now()
#         cron_logger.info("{} completed, cron log entry-{}".format(cron_log_entry.cron_name, cron_log_entry.id))
#
#     except Exception as e:
#         cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.ABORTED
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
#         cron_logger.info("{} aborted, cron log entry-{}, {}, {}, {}".format(cron_name, cron_log_entry.id,
#                                                                             exc_type, fname, exc_tb.tb_lineno))
#         traceback.print_exc()
#     cron_log_entry.save()
#
#
# def fetch_hdpos_users():
#
#     cron_logger.info('hdpos users fetch started')
#
#     date_config = GlobalConfig.objects.filter(key='hdpos_users_fetch').last()
#
#     last_date = ''
#     now_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     if date_config:
#         last_date = date_config.value
#
#     cnxn = pyodbc.connect(CONNECTION_PATH)
#     cron_logger.info('connected to hdpos marekting users fetch')
#     cursor = cnxn.cursor()
#
#     module_dir = os.path.dirname(__file__)
#     file_path = os.path.join(module_dir, 'sql/users_sql.sql')
#     fd = open(file_path, 'r')
#     sqlfile = fd.read()
#     fd.close()
#
#     specific_shops = GlobalConfig.objects.filter(key="hdpos_users_from_shops").last()
#     if specific_shops and specific_shops.value not in [None, '']:
#         shops_str = specific_shops.value
#         shops = shops_str.split('|')
#         sqlfile += " where shop.LocationName in ("
#         for loc in shops:
#             sqlfile += "'" + loc + "',"
#         sqlfile = sqlfile.strip(",")
#         sqlfile += ")"
#         if last_date != '':
#             sqlfile = sqlfile + " and customers.RegistrationDate >='" + last_date + "'"
#     else:
#         if last_date != '':
#             sqlfile = sqlfile + " where customers.RegistrationDate >='" + last_date + "'"
#
#     cursor.execute(sqlfile)
#
#     cron_logger.info('writing hdpos users data')
#
#     with transaction.atomic():
#
#         for row in cursor:
#
#             if not row[0]:
#                 continue
#
#             row[0] = '' if not row[0] else row[0].replace(' ', '')
#             row[1] = '' if not row[1] else row[1].replace(' ', '')
#             row[2] = '' if not row[2] else row[2].strip()
#
#             rule = re.compile(r'^[6-9]\d{9}$')
#             if not rule.search(str(row[0])):
#                 continue
#
#             if not User.objects.filter(phone_number=row[0]).exists():
#                 with transaction.atomic():
#                     user_obj = User.objects.create_user(phone_number=row[0], email=row[1], first_name=row[2],
#                                                         last_name=row[3])
#                     user_obj.is_active = False
#                     user_obj.save()
#                     ReferralCode.generate_user_referral_code(user_obj)
#                     RewardPoint.welcome_reward(user_obj)
#                     Profile.objects.get_or_create(profile_user=user_obj)
#                     shop_map = ShopLocationMap.objects.filter(location_name=row[4]).last()
#                     if shop_map:
#                         shop_id = shop_map.shop.id
#                         create_user_shop_mapping(user_obj, shop_id)
#
#         if date_config:
#             date_config.value = now_date
#             date_config.save()
#         else:
#             GlobalConfig.objects.create(key='hdpos_users_fetch', value=now_date)



