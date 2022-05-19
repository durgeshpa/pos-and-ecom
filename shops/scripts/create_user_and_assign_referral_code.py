# python imports
import logging
import traceback

# app imports
from django.contrib.auth.models import Group

from accounts.models import User
from marketing.models import ReferralCode, RewardPoint
from shops.models import Shop

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run():
    create_gf_user_and_assign_referral_code_along_with_group()


def create_gf_user_and_assign_referral_code_along_with_group():
    info_logger.info("create_gf_user_and_assign_referral_code_along_with_group | Started")
    print("create_gf_user_and_assign_referral_code_along_with_group | Started")
    try:
        users = {
            8619903524: "Anil",
            8750190072: "Bhupendra",
            8285394922: "Deepak",
            9205448578: "Puneet",
            9999840080: "Gaurav",
            9810494673: "Praveen",
            7500823069: "Deepak B",
            7500275923: "Vishal",
            8766288749: "Kuldeep",
            8393080383: "Akash",
            9971530198: "Sagar",
            9999082393: "Arun",
            9528404856: "Anit",
            9897682393: "Shivam",
            9897808410: "Deepak",
            8393900090: "Monti",
            9170161840: "Yogendra",
            9899856351: "Shivam k",
            9870591830: "Rajkumar",
            8130101972: "Lalit Tomar"
        }

        field_executive_group = Group.objects.filter(name='Field Executive').last()
        for phone_number, user_name in users.items():
            info_logger.info(f"\nIterating: {phone_number} -> {user_name}")
            gf_user, created = User.objects.get_or_create(phone_number=phone_number)
            if created:
                gf_user.first_name = user_name
            gf_user.groups.add(field_executive_group)
            gf_user.save()
            info_logger.info(f"Group assigned | {gf_user}")

            # Reward Point
            info_logger.info(f"Reward Point starts | {gf_user}")
            if not ReferralCode.objects.filter(user=gf_user).exists():
                rf_code_obj = ReferralCode.generate_user_referral_code(gf_user, gf_user)
                info_logger.info(f"Referral Code: {rf_code_obj} of User {gf_user} ")
                print(f"Referral Code: {rf_code_obj} of User {gf_user} ")
                reward_points, created = RewardPoint.objects.get_or_create(reward_user=gf_user)
                if created:
                    info_logger.info(f"Reward Point | Created | {gf_user}")
            else:
                user_ref_code = ReferralCode.objects.filter(user=gf_user).last()
                info_logger.info(f"Referral Code: {user_ref_code.referral_code} of User {gf_user} already exists ")
        info_logger.info("create_gf_user_and_assign_referral_code_along_with_group | Ended")
        print("create_gf_user_and_assign_referral_code_along_with_group | Ended")
    except Exception as e:
        info_logger.error(f"create_gf_user_and_assign_referral_code_along_with_group | error | {e}")
        traceback.print_exc()
