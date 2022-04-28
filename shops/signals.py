from django.dispatch import receiver

from marketing.models import ReferralCode
from django.db.models.signals import post_save, pre_save

from shops.models import Shop


@receiver(post_save, sender=Shop)
def assign_referral_code_to_shop_owner(sender, instance=None, created=False, **kwargs):
    if instance.shop_type.shop_sub_type.retailer_type_name in ['fofo', 'foco'] and instance.approval_status == 2:
        if not ReferralCode.objects.filter(user=instance.shop_owner).exists():
            ReferralCode.generate_user_referral_code(instance.shop_owner, instance.shop_owner)
