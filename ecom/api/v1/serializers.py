from rest_framework import serializers

from accounts.models import User
from addresses.models import Pincode
from marketing.models import ReferralCode, RewardPoint, RewardLog
from shops.models import Shop

from ecom.models import Address


class AccountSerializer(serializers.ModelSerializer):
    """
    E-Commerce User Account
    """
    name = serializers.SerializerMethodField()

    @staticmethod
    def get_name(obj):
        return obj.first_name + ' ' + obj.last_name if obj.first_name and obj.last_name else (
            obj.first_name if obj.first_name else '')

    class Meta:
        model = User
        fields = ('name', 'phone_number')


class RewardsSerializer(serializers.ModelSerializer):
    """
    Loyalty Points detail for a user
    """
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    referral_code = serializers.SerializerMethodField()
    welcome_points = serializers.SerializerMethodField()

    @staticmethod
    def get_phone(obj):
        return obj.reward_user.phone_number

    @staticmethod
    def get_email(obj):
        return obj.reward_user.email

    @staticmethod
    def get_referral_code(obj):
        return ReferralCode.user_referral_code(obj.reward_user)

    @staticmethod
    def get_welcome_points(obj):
        welcome_rwd_obj = RewardLog.objects.filter(reward_user=obj.reward_user,
                                                   transaction_type='welcome_reward').last()
        return welcome_rwd_obj.points if welcome_rwd_obj else 0

    class Meta:
        model = RewardPoint
        fields = ('phone', 'email', 'referral_code', 'redeemable_points', 'redeemable_discount', 'direct_earned',
                  'indirect_earned', 'points_used', 'welcome_points')


class UserLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name')


class AddressSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(required=False)
    state_name = serializers.CharField(required=False)

    class Meta:
        model = Address
        fields = ('id', 'user', 'type', 'address', 'contact_name', 'contact_number', 'pincode', 'city_name',
                  'state_name', 'default')
        read_only_fields = ['id', 'user']

    def validate(self, attrs):
        # Validate Pin Code
        pin_code_obj = Pincode.objects.filter(pincode=attrs.get('pincode')).select_related('city', 'city__state').last()
        if not pin_code_obj:
            raise serializers.ValidationError("Invalid Pin Code")
        # Check for address id in case of update
        pk = self.context.get('pk', None)
        user = self.context.get('user')
        if pk:
            try:
                Address.objects.get(user=user, id=pk)
                attrs['id'] = pk
            except:
                raise serializers.ValidationError("Invalid Address Id")
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        return Address.objects.create(**validated_data)

    def update(self, add_id, validated_data):
        add = Address.objects.get(id=add_id)
        add.type, add.address, add.contact_name = validated_data['type'], validated_data['address'], validated_data[
            'contact_name']
        add.contact_number, add.pincode, add.default = validated_data['contact_number'], validated_data[
            'pincode'], validated_data['default']
        add.save()
