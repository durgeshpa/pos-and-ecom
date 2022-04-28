# python imports
import logging
import traceback

# app imports
from accounts.models import User
from marketing.models import ReferralCode, RewardPoint
from shops.models import Shop

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run():
    assign_referral_code_to_shop_owner()
    assign_referral_code_to_gf_employees()


def assign_referral_code_to_shop_owner():

    try:
        info_logger.info('assign_referral_code_to_shop_owner |started')
        shop_owner_obj = Shop.objects.filter(shop_type__shop_sub_type__retailer_type_name__in=['fofo', 'foco'],
                                             approval_status=2)

        for cnt, shop_owner in enumerate(shop_owner_obj):
            if not ReferralCode.objects.filter(user=shop_owner.shop_owner).exists():
                rf_code_obj = ReferralCode.generate_user_referral_code(shop_owner.shop_owner, shop_owner.shop_owner)
                info_logger.info(f"{cnt + 1} | Referral Code: {rf_code_obj} of User {shop_owner.shop_owner} "
                                 f" Shop Name--> {shop_owner.shop_name}")
                print(f"{cnt + 1} | Referral Code: {rf_code_obj} of User {shop_owner.shop_owner} "
                      f" Shop Name--> {shop_owner.shop_name}")
                RewardPoint.objects.get_or_create(user=shop_owner.shop_owner)
            else:
                info_logger.info(f"{cnt + 1} | Referral Code of User {shop_owner.shop_owner} already exists ")
                print(f"{cnt + 1} | Referral Code of User {shop_owner.shop_owner} already exists ")
        info_logger.info('assign_referral_code_to_shop_owner | completed')
    except Exception as e:
        info_logger.error(f"assign_referral_code_to_shop_owner | error | {e}")
        traceback.print_exc()


def assign_referral_code_to_gf_employees():
    try:
        info_logger.info('assign_referral_code_to_gf_employees |started')
        gf_users = User.objects.filter(groups__name__in=['Field Executive', 'Digital Marketing', 'Marketing'])
        for cnt, gf_user in enumerate(gf_users):
            if not ReferralCode.objects.filter(user=gf_user).exists():
                rf_code_obj = ReferralCode.generate_user_referral_code(gf_user, gf_user)
                print(rf_code_obj)
                info_logger.info(f"{cnt + 1} | Referral Code: {rf_code_obj} of User {gf_user} ")
                print(f"{cnt + 1} | Referral Code: {rf_code_obj} of User {gf_user} ")
                RewardPoint.objects.get_or_create(user=gf_user)
            else:
                info_logger.info(f"{cnt + 1} | Referral Code of User {gf_user} already exists ")
                print(f"{cnt + 1} | Referral Code of User {gf_user} already exists ")
        info_logger.info('assign_referral_code_to_gf_employees | completed')
    except Exception as e:
        info_logger.error(f"assign_referral_code_to_gf_employees | error | {e}")
        traceback.print_exc()
