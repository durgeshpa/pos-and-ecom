from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from ...models import Discount, DiscountValue
from products.api.v1.serializers import BrandSerializers, CategorySerializers
from brand.models import Brand
from categories.models import Category



class DiscountSerializer(serializers.ModelSerializer):
    """
    Get all Brand/Category Discount
    """

    class Meta:
        model = Discount
        fields = ('id', 'discount_type', 'category', 'brand', 'start_price', 'end_price', 'start_date', 'end_date')

    def validate(self, data):
        if 'start_date' in data and 'end_date' in data and data['start_date'] > data['end_date']:
            raise serializers.ValidationError(_('End Date should be greater than start date'))
        if 'start_price' in data and 'end_price' in data and data['start_price'] > data['end_price']:
            raise serializers.ValidationError(_('End Price should be greater than start price'))
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        discount = instance.discount_value
        data['discount_percentage'] = discount.discount_value
        if instance.category:
            data['category'] = CategorySerializers(instance.category).data
        else:
            data['brand'] = BrandSerializers(instance.brand).data
        return data

    @transaction.atomic()
    def create(self, validated_data):
        discount_percentage = self.context.get('discount_percentage')
        if discount_percentage > 100:
            raise serializers.ValidationError(_("Discount Percentage should not be more than 100."))
        discount_obj = DiscountValue.objects.create(is_percentage=True, discount_value=discount_percentage)
        discount = Discount.objects.create(discount_value = discount_obj, **validated_data)
        return discount
    
    @transaction.atomic()
    def update(self, instance, validated_data):
        discount_percentage = self.context.get('discount_percentage')
        if discount_percentage:
            discount_obj = instance.discount_value
            discount_obj.discount_value = discount_percentage
            discount_obj.save()
        return super().update(instance, validated_data)

