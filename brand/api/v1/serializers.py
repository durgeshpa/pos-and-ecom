from rest_framework import serializers
from brand.models import Brand,BrandPosition,BrandData

class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class BrandSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = '__all__'

class BrandPositionSerializer(serializers.ModelSerializer):

    class Meta:
        model = BrandPosition
        fields = '__all__'

class BrandDataSerializer(serializers.ModelSerializer):
    brand_data = BrandSerializer(read_only=True)
    slot = BrandPositionSerializer(read_only=True)

    class Meta:
        model = BrandData
        fields = ('id','slot','brand_data','brand_data_order')

class BrandSlotSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = BrandPosition
        fields = '__all__'

class SubBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', "brand_name", "brand_logo", "brand_code")