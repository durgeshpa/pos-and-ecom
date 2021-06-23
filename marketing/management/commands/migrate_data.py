from django.core.management.base import BaseCommand
from decouple import config
import pyodbc
import os

from pos.common_functions import create_user_shop_mapping
from franchise.models import ShopLocationMap
from marketing.models import *

CONNECTION_PATH = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + config('HDPOS_DB_HOST') \
                  + ';DATABASE=' + config('HDPOS_DB_NAME') \
                  + ';UID=' + config('HDPOS_DB_USER') \
                  + ';PWD=' + config('HDPOS_DB_PASSWORD')


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
                ref_obj, created = ReferralCode.objects.get_or_create(user=user, added_by=user)
                ref_obj.referral_code = mlmuser.referral_code
                ref_obj.created_at = mlmuser.created_at
                ref_obj.save()

                # Profile
                profile = Profile.objects.filter(user=mlmuser).last()
                if profile:
                    profile.profile_user = user
                    profile.save()

                # Reward Point
                reward_point = RewardPoint.objects.filter(user=mlmuser).last()
                if reward_point:
                    reward_point.reward_user = user
                    reward_point.save()

                # Reward Logs
                reward_logs = RewardLog.objects.filter(user=mlmuser)
                if reward_logs.exists():
                    for reward_log in reward_logs:
                        reward_log.reward_user = user
                        reward_log.save()

                # Referral
                referral_tos = Referral.objects.filter(referral_to=mlmuser)
                if referral_tos.exists():
                    for ref_to in referral_tos:
                        ref_to.referral_to_user = user
                        ref_to.save()

                referral_bys = Referral.objects.filter(referral_by=mlmuser)
                if referral_bys.exists():
                    for ref_by in referral_bys:
                        ref_by.referral_by_user = user
                        ref_by.save()
