from django.core.management.base import BaseCommand
from django.db import transaction
from decouple import config
import pyodbc

import os
import csv
import codecs

from pos.common_functions import create_user_shop_mapping
from franchise.models import ShopLocationMap

CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST') \
                  + ';DATABASE=' + config('HDPOS_DB_NAME') \
                  + ';UID=' + config('HDPOS_DB_USER') \
                  +';PWD=' + config('HDPOS_DB_PASSWORD')

from marketing.models import *


class Command(BaseCommand):
    """
        Migrate mlm users and user specific data to accounts users
    """
    def handle(self, *args, **options):
        with transaction.atomic():
            # get shop data mlmusers
            mlmphonenos = MLMUser.objects.values_list('phone_number', flat=True)
            cnxn = pyodbc.connect(CONNECTION_PATH)
            cursor = cnxn.cursor()
            module_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            file_path = os.path.join(module_dir, 'crons/sql/users_sql.sql')
            fd = open(file_path, 'r')
            sqlfile = fd.read()
            fd.close()
            sqlfile += " where contacts.MobileNumber in ('" + "','".join(mlmphonenos) + "')"
            cursor.execute(sqlfile)

            phone_shop_map = {}
            for row in cursor:
                shop = ShopLocationMap.objects.filter(location_name=row[4]).last()
                if shop:
                    phone_shop_map[row[0]] = shop.shop.id

            mlmusers = MLMUser.objects.all()
            for mlmuser in mlmusers:
                # user creation
                if not User.objects.filter(phone_number=mlmuser.phone_number).exists():
                    email = mlmuser.email if mlmuser.email else ''
                    name = mlmuser.name if mlmuser.name else ''
                    user = User.objects.create_user(phone_number=mlmuser.phone_number, email=email, first_name=name)
                    if mlmuser.status == 0:
                        user.is_active = False
                        user.save()
                else:
                    print("user exists {}".format(mlmuser.phone_number))
                    user = User.objects.filter(phone_number=mlmuser.phone_number).last()

                if mlmuser.phone_number in phone_shop_map:
                    create_user_shop_mapping(user, phone_shop_map[mlmuser.phone_number])

                # referral code store in different model
                ref_obj, created = ReferralCode.objects.get_or_create(user=user)
                ref_obj.referral_code = mlmuser.referral_code
                ref_obj.save()

                # Create profiles for all users
                Profile.objects.get_or_create(user=user)

            # Other models
            module_dir = os.path.dirname(__file__)
            reward_file_path = os.path.join(module_dir, 'reward_point.csv')
            reward_file = open(reward_file_path, 'rb')
            reward_reader = csv.reader(codecs.iterdecode(reward_file, 'utf-8'))
            for row in reward_reader:
                mlmuser = MLMUser.objects.get(pk=row[0])
                user = User.objects.get(phone_number=mlmuser.phone_number)
                RewardPoint.objects.create(user=user, direct_users=row[1], indirect_users=row[2], direct_earned=row[3],
                                           indirect_earned=row[4], points_used=row[5])

            log_file_path = os.path.join(module_dir, 'reward_log.csv')
            log_file = open(log_file_path, 'rb')
            log_reader = csv.reader(codecs.iterdecode(log_file, 'utf-8'))
            for row in log_reader:
                mlmuser = MLMUser.objects.get(pk=row[0])
                user = User.objects.get(phone_number=mlmuser.phone_number)
                row[4] = row[4] if row[4] and row[4] != '' else 0
                if row[5] and row[5] != '':
                    changed_by = User.objects.get(pk=row[5])
                    RewardLog.objects.create(user=user, transaction_type=row[1], transaction_id=row[2], points=row[3],
                                             discount=row[4], changed_by=changed_by)
                else:
                    RewardLog.objects.create(user=user, transaction_type=row[1], transaction_id=row[2], points=row[3],
                                             discount=row[4])

            ref_file_path = os.path.join(module_dir, 'referral.csv')
            ref_file = open(ref_file_path, 'rb')
            ref_reader = csv.reader(codecs.iterdecode(ref_file, 'utf-8'))
            for row in ref_reader:
                mlmuser_refto = MLMUser.objects.get(pk=row[0])
                mlmuser_refby = MLMUser.objects.get(pk=row[1])
                user_refto = User.objects.get(phone_number=mlmuser_refto.phone_number)
                user_refby = User.objects.get(phone_number=mlmuser_refby.phone_number)
                Referral.objects.create(referral_to=user_refto, referral_by=user_refby)








