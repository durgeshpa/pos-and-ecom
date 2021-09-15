from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from ...models import CouponRuleSet, Coupon, RuleSetBrandMapping, RuleSetCategoryMapping, DiscountValue
from products.api.v1.serializers import BrandSerializers, CategorySerializers
from pos.api.v1.serializers import date_validation, coupon_name_validation
from pos.common_functions import OffersCls
from brand.models import Brand
from categories.models import Category


class CouponCreateSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    brand = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), required=False)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False)
    is_percentage = serializers.BooleanField(default=0)
    discount_value = serializers.DecimalField(
        required=True, max_digits=6, decimal_places=2, min_value=0.01)
    max_discount = serializers.DecimalField(
        max_digits=6, decimal_places=2, default=0, min_value=0)

    def validate(self, data):
        if data.get('brand') == None and data.get('category') == None:
            raise serializers.ValidationError(
                _('Provide brand for coupon type brand or category for coupon type category'))
        if data['is_percentage'] and data['discount_value'] > 100:
            raise serializers.ValidationError(
                'discount should be less than 100.')
        date_validation(data)
        return data

class CouponUpdateSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, data):
        date_validation(data)
        return data

class CouponRuleSetSerializer(serializers.ModelSerializer):
    """
    Serializer for coupon ruleset
    """

    class Meta:
        model = CouponRuleSet
        fields = ('id', 'rulename', 'rule_description',
                  'discount', 'start_date', 'expiry_date')
        depth = 1


class CouponSerializer(serializers.ModelSerializer):
    """
    Serializer for coupon
    """

    class Meta:
        model = Coupon
        fields = ('id', 'coupon_code', 'coupon_name',
                  'coupon_type', 'is_active', 'created_at', 'updated_at')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['coupon_type'] == 'category':
            category = RuleSetCategoryMapping.objects.get(
                rule=instance.rule).category
            representation['category'] = CategorySerializers(
                category).data
        elif representation['coupon_type'] == 'brand':
            brand = RuleSetBrandMapping.objects.get(rule=instance.rule).brand
            representation['brand_name'] = BrandSerializers(brand).data
        representation['rule'] = CouponRuleSetSerializer(instance.rule).data
        return representation

    def validate(self, data):
        coupon_name_validation(data.get('coupon_name'))
        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Create Coupon
        """
        data = validated_data
        discount_value = self.context.get('discount_value')
        max_discount = self.context.get('max_discount')
        is_percentage = self.context.get('is_percentage')
        brand_id = self.context.get('brand')
        if brand_id:
            brand = Brand.objects.get(id=brand_id)
        else:
            category = Category.objects.get(id=self.context.get('category'))
        discount_value_str = str(discount_value)
        if is_percentage:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value,
                                                        max_discount=max_discount, is_percentage=True)
            if discount_obj.max_discount and float(discount_obj.max_discount) > 0:
                max_discount_str = str(discount_obj.max_discount)
                coupon_code = discount_value_str + "% off upto ₹" + max_discount_str
            else:
                coupon_code = discount_value_str + "% off"
        else:
            discount_obj = DiscountValue.objects.create(
                discount_value=discount_value, is_percentage=False)
            coupon_code = "₹" + discount_value_str + " off"

        if brand_id:
            coupon_code = coupon_code + " on brand " + brand.brand_name
            rulename = brand.brand_name + '_' + str(discount_obj.discount_value)
        else:
            coupon_code = coupon_code + " on category " + category.category_name
            rulename = category.category_name + '_' + str(discount_obj.discount_value)

        ruledescription = coupon_code
        if CouponRuleSet.objects.filter(rulename=rulename).exists():
            coupon_obj = "Offer with same Order Value and Discount Detail already exists"
        else:
            coupon_obj = CouponRuleSet.objects.create(rulename=rulename, rule_description=ruledescription, is_active=True,
                                                      start_date=self.context['start_date'], expiry_date=self.context['end_date'], discount=discount_obj, all_users=True)
        if type(coupon_obj) == str:
            raise serializers.ValidationError(_(coupon_obj))
        if brand_id:
            RuleSetBrandMapping.objects.create(rule=coupon_obj, brand=brand)
        else:
            RuleSetCategoryMapping.objects.create(rule=coupon_obj, category=category)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, data['coupon_type'], data['coupon_name'], rulename, None, self.context.get(
            'start_date'), self.context.get('end_date'))

        return coupon

    @transaction.atomic()
    def update(self, instance, validated_data):
        """
        Update Coupon
        """
        data = validated_data
        coupon_name_validation(data)
        context_data = self.context.get('data')
        try:
            rule = CouponRuleSet.objects.get(id=instance.rule.id)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(_("Coupon Ruleset not found"))

        instance.coupon_name = data['coupon_name'] if 'coupon_name' in data else instance.coupon_name
        if 'start_date' in context_data:
            rule.start_date = instance.start_date = context_data['start_date']
        if 'end_date' in context_data:
            rule.expiry_date = instance.expiry_date = context_data['end_date']
        if 'is_active' in context_data:
            rule.is_active = instance.is_active = context_data['is_active']
        rule.save()
        return super().update(instance, validated_data)