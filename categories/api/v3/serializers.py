from django.db import transaction

from rest_framework import serializers
from categories.models import Category


class ParentCategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = ('id', 'category_name',)


class CategoryCrudSerializers(serializers.ModelSerializer):
    class Meta:
        model = Category

        fields = ('id', 'category_name', 'category_desc', 'category_parent',
                  'category_sku_part', 'category_image', 'updated_by', 'status')

    @transaction.atomic
    def create(self, validated_data):
        pass

    @transaction.atomic
    def update(self, instance, validated_data):
        pass