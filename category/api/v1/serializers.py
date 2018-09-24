from rest_framework import serializers
from category.models import Categories,CategoryPosation

class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class CategoriesSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = Categories
        fields = ('id','category_name','category_desc','cat_parent','category_sku_part','category_image','is_created','is_modified','status')
