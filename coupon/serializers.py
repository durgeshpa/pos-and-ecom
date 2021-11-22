from rest_framework import serializers
from .models import *


class CouponSerializer(serializers.ModelSerializer):
    is_applied = serializers.SerializerMethodField()
    max_qty = serializers.SerializerMethodField()
    class Meta:
        model = Coupon
        fields = ('coupon_name', 'coupon_code', 'coupon_type', 'is_applied', 'max_qty')

    def get_is_applied(self, obj):
        status = False
        return status

    def get_max_qty(self, obj):
        return -1
