import datetime
import sys
import os
from django.db import transaction
from django.utils import timezone
import traceback
import logging

from services.models import CronRunLog
from global_config.models import GlobalConfig
from marketing.models import RewardPoint, RewardLog
from marketing.sms import SendSms

cron_logger = logging.getLogger('cron_log')

def rewards_notify_users():

    cron_name = CronRunLog.CRON_CHOICE.MARKETING_REWARDS_NOTIFY
    if CronRunLog.objects.filter(cron_name=cron_name, status=CronRunLog.CRON_STATUS_CHOICES.STARTED).exists():
        cron_logger.info("{} already running".format(cron_name))
        return

    cron_log_entry = CronRunLog.objects.create(cron_name=cron_name)
    cron_logger.info("{} started, cron log entry-{}"
                     .format(cron_log_entry.cron_name, cron_log_entry.id))

    try:
        notify()
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


def notify():

    cron_logger.info('rewards notification marketing started')

    date_config = GlobalConfig.objects.filter(key='rewards_last_notification_time').last()

    now_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if date_config:
        last_date = date_config.value
        rewards = RewardLog.objects.filter(created_at__gte=last_date, created_at__lt=now_date,
                                 transaction_type__in=['direct_reward', 'indirect_reward']).values('reward_user').distinct()
    else:
        rewards = RewardLog.objects.filter(created_at__lt=now_date, transaction_type__in=['direct_reward',
                                                                                          'indirect_reward']).values('reward_user').distinct()
    with transaction.atomic():

        for user in rewards:
            reward_obj = RewardPoint.objects.filter(reward_user=user['reward_user']).last()
            if reward_obj:
                n_users = reward_obj.direct_users + reward_obj.indirect_users
                total_points = (reward_obj.direct_earned + reward_obj.indirect_earned) - reward_obj.points_used
                try:
                    conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
                    used_reward_factor = int(conf_obj.value)
                except:
                    used_reward_factor = 4
                message = SendSms(phone=reward_obj.reward_user.phone_number,
                                  body="Congratulations, you have won {} reward points because {} friends"
                                       " shopped using your referral code! Shop at PepperTap store and avail discounts"
                                       " upto {} INR"
                                  .format(total_points, n_users, int(total_points / used_reward_factor)))

                message.send()

        if date_config:
            date_config.value = now_date
            date_config.save()
        else:
            GlobalConfig.objects.create(key='rewards_last_notification_time', value=now_date)



