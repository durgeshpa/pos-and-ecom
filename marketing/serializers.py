from rest_framework import serializers
from .models import PhoneOTP, RewardPoint, Profile, RewardLog
from global_config.models import GlobalConfig

class PhoneOTPValidateSerializer(serializers.ModelSerializer):
    """
    validate the otp send to number
    """

    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
            'otp'
        )


class SendSmsOTPSerializer(serializers.ModelSerializer):
    """
    Send OTP SMS to number
    """

    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )


class RewardsSerializer(serializers.ModelSerializer):
    direct_users_count = serializers.SerializerMethodField('direct_users')
    indirect_users_count = serializers.SerializerMethodField('indirect_users')
    direct_earned_points = serializers.SerializerMethodField('direct_earned')
    indirect_earned_points = serializers.SerializerMethodField('indirect_earned')
    total_points_used = serializers.SerializerMethodField('points_used')
    total_earned_points = serializers.SerializerMethodField('total_earned')
    remaining_points = serializers.SerializerMethodField('remaining')
    welcome_reward_point = serializers.SerializerMethodField('welcome_reward')
    discount_point = serializers.SerializerMethodField('discount')

    class Meta:
        model = RewardPoint
        fields = ('direct_users_count', 'indirect_users_count', 'direct_earned_points', 'indirect_earned_points',
                  'total_points_used', 'total_earned_points', 'remaining_points', 'welcome_reward_point',
                  'discount_point')

    def direct_users(self, obj):
        return str(obj.direct_users)

    def indirect_users(self, obj):
        return str(obj.indirect_users)

    def direct_earned(self, obj):
        return str(obj.direct_earned)

    def indirect_earned(self, obj):
        return str(obj.indirect_earned)

    def points_used(self, obj):
        return str(obj.points_used)

    def total_earned(self, obj):
        return str(obj.direct_earned + obj.indirect_earned)

    def remaining(self, obj):
        return str(obj.direct_earned + obj.indirect_earned - obj.points_used)

    def welcome_reward(self, obj):
        return str(RewardLog.objects.filter(user=obj.user, transaction_type='welcome_reward').last().points)

    def discount(self, obj):
        try:
            conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
            used_reward_factor = int(conf_obj.value)
        except:
            used_reward_factor = 4
        return str(int((obj.direct_earned + obj.indirect_earned - obj.points_used)/used_reward_factor))



class ProfileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['image']
