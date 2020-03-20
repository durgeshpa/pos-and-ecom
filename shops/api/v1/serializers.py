import re

from rest_framework import serializers

from shops.models import (RetailerType, ShopType, Shop, ShopPhoto,
    ShopRequestBrand, ShopDocument, ShopUserMapping, SalesAppVersion, ShopTiming,
    FavouriteProduct
)
from django.contrib.auth import get_user_model
from accounts.api.v1.serializers import UserSerializer,GroupSerializer
from retailer_backend.validators import MobileNumberValidator
from rest_framework import validators

from products.models import Product, ProductImage
#from retailer_to_sp.api.v1.serializers import ProductImageSerializer #ProductSerializer

User =  get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductImage
      fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    product_price = serializers.SerializerMethodField()
    product_mrp = serializers.SerializerMethodField()
    cash_discount = serializers.SerializerMethodField()
    loyalty_incentive = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        if ProductImage.objects.filter(product=obj).exists():
            product_image = ProductImage.objects.filter(product=obj)[0].image.url
            return product_image
        else:
            return None

    def get_product_price(self, obj):
        parent = self.context.get('parent', None)
        if parent:
            return obj.getRetailerPrice(parent)

    def get_product_mrp(self, obj):
        parent = self.context.get('parent', None)
        if parent:
            return obj.getMRP(parent)

    def get_cash_discount(self, obj):
        parent = self.context.get('parent', None)
        if parent:
            return obj.getCashDiscount(parent) 

    def get_loyalty_incentive(self, obj):
        parent = self.context.get('parent', None)
        if parent:
            return obj.getLoyaltyIncentive(parent) 

    class Meta:
        model = Product
        fields = ('id','product_name','product_inner_case_size',
            'product_case_size', 'product_image', 'product_price',
             'product_mrp', 'cash_discount', 'loyalty_incentive',
            )

class ListFavouriteProductSerializer(serializers.ModelSerializer):
    #product = ProductSerializer(many=True)

    class Meta:
        model = FavouriteProduct
        fields = ('id', 'buyer_shop', 'product')


class AddFavouriteProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = FavouriteProduct
        fields = ('id', 'buyer_shop', 'product')


class FavouriteProductSerializer(serializers.ModelSerializer):

    product = serializers.SerializerMethodField()   

    def get_product(self, obj):
        parent = obj.buyer_shop.retiler_mapping.last().parent.id
        product = obj.product
        return ProductSerializer(product, context={'parent': parent}).data

    class Meta:
        model = FavouriteProduct
        fields = ('id', 'buyer_shop', 'product') 


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

    def validate_shop_document_number(self, data):
        if ShopDocument.objects.filter(shop_document_number=data).exists():
            raise serializers.ValidationError('Document number is already registered')
        return data

    def validate(self, data):
        if data.get('shop_document_type') == ShopDocument.GSTIN:
            gst_regex = "^([0]{1}[1-9]{1}|[1-2]{1}[0-9]{1}|[3]{1}[0-7]{1})([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$"
            if not re.match(gst_regex, data.get('shop_document_number')):
                raise serializers.ValidationError({'user_document_number': 'Please enter valid pan card no.'})
        return data

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['shop_name'] = ShopSerializer(instance.shop_name).data
        return response

class ShopRequestBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopRequestBrand
        fields = '__all__'

class ShopUserMappingSerializer(serializers.ModelSerializer):
    shop = ShopSerializer()
    employee = UserSerializer()
    employee_group = GroupSerializer()

    class Meta:
        model = ShopUserMapping
        fields = ('shop','manager','employee','employee_group','created_at','status')


class SellerShopSerializer(serializers.ModelSerializer):
    shop_owner = serializers.CharField(max_length=10, allow_blank=False, trim_whitespace=True, validators=[MobileNumberValidator])

    class Meta:
        model = Shop
        fields = ('id', 'shop_owner', 'shop_name', 'shop_type', 'imei_no')
        extra_kwargs = {
            'shop_owner': {'required': True},
        }


class AppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesAppVersion
        fields = ('app_version', 'update_recommended','force_update_required')


class ShopUserMappingUserSerializer(serializers.ModelSerializer):
    employee = UserSerializer()

    class Meta:
        model = ShopUserMapping
        fields = ('shop','manager','employee','employee_group','created_at','status')


class ShopTimingSerializer(serializers.ModelSerializer):
    SUN = 'SUN'
    MON = 'MON'
    TUE = 'TUE'
    WED = 'WED'
    THU = 'THU'
    FRI = 'FRI'
    SAT = 'SAT'

    off_day_choices = (
        (SUN, 'Sunday'),
        (MON, 'Monday'),
        (TUE, 'Tuesday'),
        (WED, 'Wednesday'),
        (THU, 'Thuresday'),
        (FRI, 'Friday'),
        (SAT, 'Saturday'),
    )

    class Meta:
        model = ShopTiming
        fields = ('shop','open_timing','closing_timing','break_start_time','break_end_time','off_day')
        read_only_fields = ('shop',)
