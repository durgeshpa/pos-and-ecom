from rest_framework import serializers
from .models import *


class CouponSerializer(serializers.ModelSerializer):
    is_applied = serializers.SerializerMethodField()
    max_qty = serializers.SerializerMethodField()
    class Meta:
        model = Coupon
        fields = ('coupon_name', 'coupon_code', 'is_applied', 'max_qty')

    def get_is_applied(self, obj):
        status = False
        return status

    def get_max_qty(self, obj):
        for product_coupon in obj.rule.product_ruleset.all():
            if product_coupon.max_qty_per_use > 0:
                max_qty = product_coupon.max_qty_per_use
            else:
                max_qty = '-'
        return max_qty
