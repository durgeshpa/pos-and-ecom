from rest_framework import serializers
from .models import *


class CouponSerializer(serializers.ModelSerializer):
    is_applied = serializers.SerializerMethodField()
    class Meta:
        model = Coupon
        fields = ('coupon_name', 'coupon_code', 'is_applied')

    def get_is_applied(self, obj):
        status = False
        return status
