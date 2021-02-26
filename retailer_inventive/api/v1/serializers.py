
from rest_framework import serializers

from retailer_inventive.models import SchemeShopMapping, SchemeSlab


class SchemeSlabSerializer(serializers.ModelSerializer):

    def validate(self, data):
        if data['min_value'] > data['max_value']:
            raise serializers.ValidationError("min_value must be less than max value")
        return data

    class Meta:
        model = SchemeSlab
        fields = ('scheme', 'min_value', 'max_value', 'discount_value', 'discount_type')




class SchemeShopMappingSerializer(serializers.ModelSerializer):

    scheme_slab = SchemeSlabSerializer()

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("start_date must be earlier than end_date")
        return data

    class Meta:
        model = SchemeShopMapping
        fields = ('scheme', 'shop', 'start_date', 'end_date', 'is_active')
