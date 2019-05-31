from rest_framework import serializers
from shops.models import (RetailerType, ShopType, Shop, ShopPhoto, ShopDocument, ShopTiming)
from django.contrib.auth import get_user_model
from rest_framework import validators

User =  get_user_model()

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
