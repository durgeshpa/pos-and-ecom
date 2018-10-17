from rest_framework import serializers
from categories.models import Category,CategoryPosation,CategoryData

class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class CategorySerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id','category_name','category_desc','cat_parent','category_sku_part','category_image','is_created','is_modified','status')


class CategoryPosSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryPosation
        fields = '__all__'


class CategoryDataSerializer(serializers.ModelSerializer):
    category_pos = CategoryPosSerializer()
    category_data = CategorySerializer()
    class Meta:
        model = CategoryData
        fields = ('id','category_pos','category_data','category_data_order')