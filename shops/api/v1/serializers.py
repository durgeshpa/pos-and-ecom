import re
import datetime
from rest_framework import serializers

from shops.models import (RetailerType, ShopType, Shop, ShopPhoto,
    ShopRequestBrand, ShopDocument, ShopUserMapping, SalesAppVersion, ShopTiming,
    FavouriteProduct, DayBeatPlanning, ExecutiveFeedback
)
from django.contrib.auth import get_user_model
from accounts.api.v1.serializers import UserSerializer,GroupSerializer
from retailer_backend.validators import MobileNumberValidator
from rest_framework import validators

from products.models import Product, ProductImage
#from retailer_to_sp.api.v1.serializers import ProductImageSerializer #ProductSerializer
from retailer_backend.messages import ERROR_MESSAGES, SUCCESS_MESSAGES
from django.db.models import Q


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
        if ShopDocument.objects.filter(~Q(shop_name_id=self.context.get('request').POST.get('shop_name')), shop_document_number=data).exists():
            raise serializers.ValidationError('Document number is already registered')
        return data

    def validate(self, data):
        if data.get('shop_document_type') == ShopDocument.GSTIN:
            gst_regex = "^([0]{1}[1-9]{1}|[1-2]{1}[0-9]{1}|[3]{1}[0-7]{1})([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$"
            if not re.match(gst_regex, data.get('shop_document_number')):
                raise serializers.ValidationError({'shop_document_number': 'Please enter valid GSTIN'})
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


class BeatShopSerializer(serializers.ModelSerializer):
    """
    Shop Serializer for Beat Plan
    """
    contact_number = serializers.SerializerMethodField()

    @staticmethod
    def get_contact_number(obj):
        """

        :param obj: day beat plan object
        :return: shop contact number
        """
        return obj.shipping_address.address_contact_number

    class Meta:
        """ Meta class """
        model = Shop
        fields = ('id', 'shop_name', 'get_shop_shipping_address', 'get_shop_pin_code', 'contact_number')


class FeedBackSerializer(serializers.ModelSerializer):
    """
    Beat Plan Serializer
    """

    class Meta:
        """ Meta class """
        model = ExecutiveFeedback
        fields = ('id', 'day_beat_plan', 'executive_feedback', 'feedback_date',)


class DayBeatPlanSerializer(serializers.ModelSerializer):
    """
    Beat Plan Serializer
    """
    shop = BeatShopSerializer()
    feedback = serializers.SerializerMethodField()

    @staticmethod
    def get_feedback(obj):
        """

        :param obj: day beat plan obj
        :return: serializer of feedback model
        """
        serializer = FeedBackSerializer(obj.day_beat_plan, many=True).data
        return serializer

    class Meta:
        """ Meta class """
        model = DayBeatPlanning
        fields = ('id', 'beat_plan', 'shop_category', 'beat_plan_date', 'next_plan_date', 'temp_status',
                  'shop', 'feedback')


class FeedbackCreateSerializers(serializers.ModelSerializer):
    """
    Applied Sales Executive Feedback
    """
    day_beat_plan = serializers.SlugRelatedField(queryset=DayBeatPlanning.objects.all(), slug_field='id', required=True)
    executive_feedback = serializers.CharField(required=True, max_length=25)
    feedback_date = serializers.DateField(required=True)

    class Meta:
        """
        Applied executive feedback create meta class
        """
        model = ExecutiveFeedback
        fields = ('id', 'day_beat_plan', 'executive_feedback', 'feedback_date', 'created_at', 'modified_at')

    def create(self, validated_data):
        """

        :param validated_data: data which comes from post method
        :return: instance otherwise error message
        """

        # condition to check same reference of Day Beat Plan with same date is exist or not
        executive_feedback = ExecutiveFeedback.objects.filter(day_beat_plan=validated_data['day_beat_plan'],
                                                              feedback_date=validated_data['feedback_date'])
        if not executive_feedback:
            # create instance of Executive Feedback
            instance, created = (ExecutiveFeedback.objects.get_or_create(
                day_beat_plan=validated_data['day_beat_plan'], executive_feedback=validated_data['executive_feedback'],
                feedback_date=validated_data['feedback_date']))
            if created:
                # condition to check if executive apply "Could Not Visit" for less than equal to 5 within the same date
                # then assign next visit date and beat plan date accordingly
                if (ExecutiveFeedback.objects.filter(executive_feedback=5, feedback_date=validated_data['feedback_date']
                                                     ).count() <= 5) and instance.executive_feedback == '5':
                    day_beat_plan = DayBeatPlanning.objects.filter(id=validated_data['day_beat_plan'].id)
                    if day_beat_plan[0].shop_category == "P1":
                        next_visit_date = validated_data['feedback_date'] + datetime.timedelta(days=1)
                        beat_plan_date = day_beat_plan[0].beat_plan_date + datetime.timedelta(days=7)
                        temp_status = True
                    elif day_beat_plan[0].shop_category == "P2":
                        next_visit_date = validated_data['feedback_date'] + datetime.timedelta(days=2)
                        beat_plan_date = day_beat_plan[0].beat_plan_date + datetime.timedelta(days=14)
                        temp_status = True
                    else:
                        next_visit_date = validated_data['feedback_date'] + datetime.timedelta(days=3)
                        beat_plan_date = day_beat_plan[0].beat_plan_date + datetime.timedelta(days=28)
                        temp_status = True

                # condition to check if executive apply feedback which is not related to "Could Not Visit" and also
                # check next visit date condition for rest of the feedback
                else:
                    day_beat_plan = DayBeatPlanning.objects.filter(id=validated_data['day_beat_plan'].id)
                    if day_beat_plan[0].shop_category == "P1" and day_beat_plan[0].temp_status is False:
                        next_visit_date = day_beat_plan[0].beat_plan_date + datetime.timedelta(days=7)
                        beat_plan_date = next_visit_date
                        temp_status = False

                    elif day_beat_plan[0].shop_category == "P2" and day_beat_plan[0].temp_status is False:
                        next_visit_date = day_beat_plan[0].beat_plan_date + datetime.timedelta(days=14)
                        beat_plan_date = next_visit_date
                        temp_status = False

                    elif day_beat_plan[0].shop_category == "P3" and day_beat_plan[0].temp_status is False:
                        next_visit_date = day_beat_plan[0].beat_plan_date + datetime.timedelta(days=28)
                        beat_plan_date = next_visit_date
                        temp_status = False
                    else:
                        next_visit_date = day_beat_plan[0].beat_plan_date
                        beat_plan_date = next_visit_date
                        temp_status = False

                # Create Data for next visit in Day Beat Planning
                DayBeatPlanning.objects.get_or_create(shop_category=day_beat_plan[0].shop_category,
                                                      next_plan_date=next_visit_date,
                                                      beat_plan_date=beat_plan_date,
                                                      shop=day_beat_plan[0].shop,
                                                      beat_plan=day_beat_plan[0].beat_plan,
                                                      temp_status=temp_status)

                # return executive feedback instance
                return instance
            # return error message
            raise serializers.ValidationError(ERROR_MESSAGES['4011'])
        # return error message
        raise serializers.ValidationError(ERROR_MESSAGES['4011'])
