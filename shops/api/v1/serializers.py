from rest_framework import serializers
from shops.models import (
    RetailerType, ShopType, Shop, ShopPhoto, ShopDocument, FavouriteProduct)
from django.contrib.auth import get_user_model
from rest_framework import validators

from products.models import Product
#from retailer_to_sp.api.v1.serializers import ProductSerializer

User =  get_user_model()



class ProductSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        if ProductImage.objects.filter(product=obj).exists():
            product_image = ProductImage.objects.filter(product=obj)[0].image.url
            return product_image
        else:
            return None

    class Meta:
        model = Product
        fields = ('id','product_name','product_inner_case_size',
            'product_case_size', 'product_image'
            )



class FavouriteProductSerializer(serializers.ModelSerializer):
    # name, size, image, price, mrp
    # need to add margin, cash_discount, loyalty discount
    product = ProductSerializer()    
    product_price = serializers.SerializerMethodField()
    product_mrp = serializers.SerializerMethodField()
    cash_discount = serializers.SerializerMethodField()
    loyalty_incentive = serializers.SerializerMethodField()

    def get_product_price(self, obj):
        # fetch product price from parent-retailer-mapping
        return obj.product.getRetailerPrice(obj.buyer_shop.shop_id) #getMRP(self,)

    def get_product_mrp(self, obj):
        # fetch product price from parent-retailer-mapping
        return obj.product.getMRP(obj.buyer_shop.shop_id)

    def get_cash_discount(self, obj):
        # fetch product price from parent-retailer-mapping
        return obj.product.getCashDiscount(obj.buyer_shop.shop_id) 

    def get_loyalty_incentive(self, obj):
        # fetch product price from parent-retailer-mapping
        return obj.product.getLoyaltyIncentive(obj.buyer_shop.shop_id) 

    class Meta:
        model = FavouriteProduct
        fields = ('id', 'product', 'product_price', 'product_mrp', 'cash_discount', 'loyalty_incentive') 


class RetailerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerType
        fields = '__all__'

class ShopTypeSerializer(serializers.ModelSerializer):
    shop_type = serializers.SerializerMethodField()

    def get_shop_type(self, obj):
        return obj.get_shop_type_display()

    class Meta:
        model = ShopType
        fields = '__all__'
        #extra_kwargs = {
        #    'shop_sub_type': {'required': True},
        #}

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_sub_type'] = RetailerTypeSerializer(instance.shop_sub_type).data
        return response



class ShopSerializer(serializers.ModelSerializer):
    shop_id = serializers.SerializerMethodField('my_shop_id')

    def my_shop_id(self, obj):
        return obj.id

    class Meta:
        model = Shop
        fields = ('id','shop_name','shop_type','imei_no','shop_id')

class ShopPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopPhoto
        fields = ('__all__')
        extra_kwargs = {
            'shop_name': {'required': True},
            'shop_photo': {'required': True},
            }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response

class ShopDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopDocument
        fields = ('__all__')
        extra_kwargs = {
            'shop_name': {'required': True},
            }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response
