from django.core.management.base import BaseCommand
from django.db import transaction

from marketing.models import *
from marketing.views import generate_user_referral_code


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
                if Profile.objects.filter(user=mlmuser).exists():
                    profile = Profile.objects.filter(user=mlmuser).last()
                    profile.new_user = user
                    profile.save()
                else:
                    Profile.objects.create(user=mlmuser, new_user=user)

                # Add accounts user to reward model
                if RewardPoint.objects.filter(user=mlmuser).exists():
                    rpo = RewardPoint.objects.filter(user=mlmuser).last()
                    rpo.new_user = user
                    rpo.save()

                # Add accounts user to reward log model
                if RewardLog.objects.filter(user=mlmuser).exists():
                    rlo = RewardLog.objects.filter(user=mlmuser).all()
                    for rl in rlo:
                        rl.new_user = user
                        rl.save()

            # Add new referral_to and referral_by to reference accounts users in existing referrals
            referrals = Referral.objects.all()
            for referral in referrals:
                referral_by_phone = referral.referral_by.phone_number
                referral_by_user = User.objects.filter(phone_number=referral_by_phone).last()
                referral_to_phone = referral.referral_to.phone_number
                referral_to_user = User.objects.filter(phone_number=referral_to_phone).last()
                if referral_to_user and referral_by_user:
                    referral.new_referral_by = referral_by_user
                    referral.new_referral_to = referral_to_user
                    referral.save()
                else:
                    print("user does not exist {} - {}".format(referral.referral_by.phone_number, referral.referral_to.phone_number))






