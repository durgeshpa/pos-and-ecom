from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from global_config.models import GlobalConfig

from .models import RewardPoint, Profile, RewardLog


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

    @staticmethod
    def direct_users(obj):
        return str(obj.direct_users)

    @staticmethod
    def indirect_users(obj):
        return str(obj.indirect_users)

    @staticmethod
    def direct_earned(obj):
        return str(obj.direct_earned)

    @staticmethod
    def indirect_earned(obj):
        return str(obj.indirect_earned)

    @staticmethod
    def points_used(obj):
        return str(obj.points_used)

    @staticmethod
    def total_earned(obj):
        return str(obj.direct_earned + obj.indirect_earned)

    @staticmethod
    def remaining(obj):
        return str(obj.direct_earned + obj.indirect_earned - obj.points_used)

    @staticmethod
    def welcome_reward(obj):
        return str(RewardLog.objects.filter(user=obj.user, transaction_type='welcome_reward').last().points)

    @staticmethod
    def discount(obj):
        try:
            conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
            used_reward_factor = int(conf_obj.value)
        except ObjectDoesNotExist:
            used_reward_factor = 4
        return str(int((obj.direct_earned + obj.indirect_earned - obj.points_used) / used_reward_factor))


class ProfileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['image']
