from rest_framework import serializers
from categories.models import Category,CategoryPosation,CategoryData
from brand.models import Brand


class SubCategorySerializer(serializers.Serializer):

    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_desc', 'category_slug', 'category_sku_part', 'category_image',
                  'status',)


class CategoryPosSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryPosation
        fields = '__all__'


class CategoryDataSerializer(serializers.ModelSerializer):
    category_pos = CategoryPosSerializer()
    category_data = CategorySerializer()

    class Meta:
        model = CategoryData
        fields = ('id', 'category_pos', 'category_data', 'category_data_order')


class BrandSerializer(serializers.ModelSerializer):

    class Meta:
        model = Brand
        fields = '__all__'


class AllCategorySerializer(serializers.ModelSerializer):
    cat_parent = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'category_name', 'cat_parent', 'category_desc', 'category_slug',
                  'category_sku_part', 'category_image', 'status',)
