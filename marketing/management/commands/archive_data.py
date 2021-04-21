import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from marketing.models import *


class Command(BaseCommand):
    """
        Migrate mlm users and user specific data to accounts users
    """
    def handle(self, *args, **options):
        with transaction.atomic():
            module_dir = os.path.dirname(__file__)
            reward_file_path = os.path.join(module_dir, 'reward_point.csv')
            with open(reward_file_path, 'w') as rf:
                reward_writer = csv.writer(rf)
                for obj in RewardPoint.objects.values('user_id', 'direct_users', 'indirect_users', 'direct_earned',
                                                      'indirect_earned', 'points_used'):
                    reward_writer.writerow(list(obj.values()))

            log_file_path = os.path.join(module_dir, 'reward_log.csv')
            with open(log_file_path, 'w') as rlf:
                log_writer = csv.writer(rlf)
                for obj in RewardLog.objects.values('user_id', 'transaction_type', 'transaction_id', 'points',
                                                      'discount', 'changed_by'):
                    log_writer.writerow(list(obj.values()))

            referral_file_path = os.path.join(module_dir, 'referral.csv')
            with open(referral_file_path, 'w') as rrf:
                referral_writer = csv.writer(rrf)
                for obj in Referral.objects.values('referral_to_id', 'referral_by_id'):
                    referral_writer.writerow(list(obj.values()))

            RewardPoint.objects.all().delete()
            RewardLog.objects.all().delete()
            Profile.objects.all().delete()
            Referral.objects.all().delete()




