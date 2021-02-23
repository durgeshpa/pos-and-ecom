from django.core.management.base import BaseCommand
from django.db import transaction

import os
import csv
import codecs

from marketing.models import *


class Command(BaseCommand):
    """
        Migrate mlm users and user specific data to accounts users
    """
    def handle(self, *args, **options):
        with transaction.atomic():
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

                # referral code store in different model
                ref_obj, created = ReferralCode.objects.get_or_create(user=user)
                ref_obj.referral_code = mlmuser.referral_code
                ref_obj.save()

                # Create profiles for all users
                Profile.objects.create(user=user)

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








