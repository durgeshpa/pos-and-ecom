from rest_framework import serializers
from brand.models import Brand,BrandPosition,BrandData
from products.api.v1.serializers import UserSerializers, LogSerializers


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


class ParentBrandSerializers(serializers.ModelSerializer):
    class Meta:
        model = Brand

        fields = ('id', 'brand_name',)


class BrandCrudSerializers(serializers.ModelSerializer):
    brand_child = SubBrandSerializer(many=True, read_only=True)
    brand_parent = ParentBrandSerializers(read_only=True)
    brand_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    updated_by = UserSerializers(write_only=True, required=False)
    brand_log = LogSerializers(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = ('id', 'brand_name', 'brand_code', 'brand_parent', 'brand_description', 'updated_by', 'brand_slug',
                  'brand_logo', 'status', 'brand_child', 'categories', 'brand_log')