from rest_framework import serializers
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping

class ProductsSearchSerializer(serializers.ModelSerializer):
   class Meta:
      model = Product
      fields = '__all__'

class GramGRNProductsSearchSerializer(serializers.Serializer):
    product_name = serializers.CharField(required=True, write_only=True)
