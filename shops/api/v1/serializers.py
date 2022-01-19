import re
import datetime
from rest_framework import serializers
from datetime import datetime, timedelta

from django.core.validators import RegexValidator

from shops.models import (PosShopUserMapping, RetailerType, ShopType, Shop, ShopPhoto,
    ShopRequestBrand, ShopDocument, ShopUserMapping, SalesAppVersion, ShopTiming,
    FavouriteProduct, DayBeatPlanning, ExecutiveFeedback, USER_TYPE_CHOICES
)
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from shops.common_validators import get_psu_mapping, get_validate_shop, get_validate_user, get_validate_user_type
from accounts.api.v1.serializers import UserSerializer,GroupSerializer
from retailer_backend.validators import MobileNumberValidator
from retailer_to_sp.models import Order, Payment
from products.models import Product, ProductImage
#from retailer_to_sp.api.v1.serializers import ProductImageSerializer #ProductSerializer
from retailer_backend.messages import ERROR_MESSAGES, SUCCESS_MESSAGES
from django.db.models import Q
from addresses.models import Address


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
        ref_name = 'Retailer Type v1'
        fields = '__all__'

class ShopTypeSerializer(serializers.ModelSerializer):
    shop_type = serializers.SerializerMethodField()

    def get_shop_type(self, obj):
        return obj.get_shop_type_display()

    class Meta:
        model = ShopType
        ref_name = 'Shop Type Serializer v1'
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
        ref_name = "shop"
        fields = ('id','shop_name','shop_type','imei_no','shop_id', 'latitude', 'longitude')

    # def validate(self, data):
    #     """Latitude and Longitude for retailer type shops"""
    #     shop_type = data.get('shop_type')
    #     if shop_type.shop_type == 'r':
    #         if not data.get('latitude') or not data.get('longitude'):
    #             raise serializers.ValidationError({'message':'Provide Latitude and Longitude'})
    #     return data



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

    # def validate_shop_document_number(self, data):
    #     if ShopDocument.objects.filter(~Q(shop_name_id=self.context.get('request').POST.get('shop_name')), shop_document_number=data).exists():
    #         raise serializers.ValidationError('Document number is already registered')
    #     return data

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

        if obj.shop_name_address_mapping.exists():
            address = obj.shop_name_address_mapping.only('address_contact_number').\
                values('address_contact_number').last()
            return address['address_contact_number']
        return None

    class Meta:
        """ Meta class """
        model = Shop
        fields = ('id', 'shop_name', 'get_shop_shipping_address', 'get_shop_pin_code', 'contact_number')


class FeedBackSerializer(serializers.ModelSerializer):
    """
    Beat Plan Serializer
    """
    executive_feedback_value = serializers.SerializerMethodField()

    @staticmethod
    def get_executive_feedback_value(obj):
        """

        :param obj: day beat plan obj
        :return: serializer of feedback model
        """
        if obj.executive_feedback == '1':
            executive_feedback = "Place Order"
        if obj.executive_feedback == '2':
            executive_feedback = "No Order For Today"
        if obj.executive_feedback == '3':
            executive_feedback = "Price Not Matching"
        if obj.executive_feedback == '4':
            executive_feedback = "Stock Not Available"
        if obj.executive_feedback == '5':
            executive_feedback = "Could Not Visit"
        if obj.executive_feedback == '6':
            executive_feedback = "Shop Closed"
        if obj.executive_feedback == '7':
            executive_feedback = "Owner Not available"
        if obj.executive_feedback == '8':
            executive_feedback = "BDA on Leave"
        if obj.executive_feedback == '9':
            executive_feedback = "Already ordered today"
        return executive_feedback

    class Meta:
        """ Meta class """
        model = ExecutiveFeedback
        fields = ('id', 'day_beat_plan', 'executive_feedback', 'executive_feedback_value', 'feedback_date', 'feedback_time')


class DayBeatPlanSerializer(serializers.ModelSerializer):
    """
    Beat Plan Serializer
    """
    day_beat_plan = serializers.SerializerMethodField()
    shop = BeatShopSerializer()
    feedback = serializers.SerializerMethodField()

    @staticmethod
    def get_day_beat_plan(obj):
        """

        :param obj: day beat plan obj
        :return: day beat plan id
        """
        return obj.id

    @staticmethod
    def get_feedback(obj):
        """

        :param obj: day beat plan obj
        :return: serializer of feedback model
        """
        try:
            executive_feedback = ExecutiveFeedback.objects.filter(day_beat_plan=obj)
            if executive_feedback[0].executive_feedback is '':
                return []
            serializer = FeedBackSerializer(obj.day_beat_plan, many=True).data
            return serializer
        except:
            return []

    class Meta:
        """ Meta class """
        model = DayBeatPlanning
        fields = ('day_beat_plan', 'beat_plan', 'shop_category', 'beat_plan_date', 'next_plan_date', 'temp_status',
                  'shop', 'feedback', 'is_active')


class ExecutiveReportSerializer(serializers.ModelSerializer):
    """
    This is Serializer to ger Report for Sales Executive
    """
    executive_name = serializers.SerializerMethodField()
    executive_id = serializers.SerializerMethodField()
    executive_contact_number = serializers.SerializerMethodField()
    shop_mapped = serializers.SerializerMethodField()
    shop_visited = serializers.SerializerMethodField()
    productivity = serializers.SerializerMethodField()
    num_of_order = serializers.SerializerMethodField()
    order_amount = serializers.SerializerMethodField()
    inactive_shop_mapped = serializers.SerializerMethodField()

    def get_executive_name(self, obj):
        """

        :param obj: object of shop user mapping
        :return: executive first name
        """
        return obj.employee.first_name

    def get_executive_id(self, obj):
        return obj.employee.id

    def get_executive_contact_number(self, obj):
        """

        :param obj: object of shop user mapping
        :return: executive contact_number
        """
        return obj.employee.phone_number

    def get_shop_mapped(self, obj):
        """

        :param obj: object of shop user mapping
        :return: count of shop map
        """

        previous_day_date = datetime.today() - timedelta(days=1)
        # previous_day_date = datetime.today()
        base_query = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee, is_active=True)

        # condition to check today
        if self._context['report'] is '0':
            date_beat_planning = base_query.filter(next_plan_date=datetime.today().date())
            shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        # condition to check past day
        elif self._context['report'] is '1':
            date_beat_planning = base_query.filter(next_plan_date=previous_day_date.date())
            shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        # condition to check past week
        elif self._context['report'] is '2':
            week_end_date = previous_day_date-timedelta(7)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        # condition to check past month
        else:
            week_end_date = previous_day_date - timedelta(30)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        return shop_map_count

    def get_shop_visited(self, obj):
        """

        :param obj: object of shop user mapping
        :return: count of shop visit
        """
        previous_day_date = datetime.today() - timedelta(days=1)
        # previous_day_date = datetime.today()
        base_query = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee, is_active=True)
        child_query = ExecutiveFeedback.objects.exclude(executive_feedback=5)

        #condition for today
        if self._context['report'] is '0':
            date_beat_planning = base_query.filter(next_plan_date=datetime.today().date())
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                      feedback_date=datetime.today()
                                                      ).count()

        # condition to check past day
        elif self._context['report'] is '1':
            date_beat_planning = base_query.filter(next_plan_date=previous_day_date.date())
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                            feedback_date=previous_day_date
                                                            ).count()

        # condition to check past week
        elif self._context['report'] is '2':
            week_end_date = previous_day_date - timedelta(7)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                            feedback_date__range=(week_end_date,
                                                                                  previous_day_date)
                                                            ).count()
        # condition to check past week
        else:
            week_end_date = previous_day_date - timedelta(30)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                            feedback_date__range=(
                                                                week_end_date, previous_day_date)
                                                            ).count()
        return shop_visit_count

    def get_productivity(self, obj):
        """

        :param obj: object of shop user mapping
        :return: productivity of sales executive
        """
        previous_day_date = datetime.today() - timedelta(days=1)
        #previous_day_date = datetime.today()
        base_query = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee, is_active=True)
        child_query = ExecutiveFeedback.objects.exclude(executive_feedback=5)

        # condition to check today
        if self._context['report'] is '0':
            date_beat_planning = base_query.filter(next_plan_date=datetime.today().date())
            feedback_query = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                  feedback_date=datetime.today()
                                                  ).count()
            if shop_visit_count != 0:
                productivity = "{:.2f}%".format(float(shop_visit_count / feedback_query) * 100)
            else:
                productivity = str(00.00) + '%'

        # condition to check past day
        elif self._context['report'] is '1':
            date_beat_planning = base_query.filter(next_plan_date=previous_day_date.date())
            feedback_query = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                  feedback_date=previous_day_date
                                                  ).count()
            if shop_visit_count != 0:
                productivity = "{:.2f}%".format(float(shop_visit_count / feedback_query) * 100)
            else:
                productivity = str(00.00) + '%'
        # condition to check past week
        elif self._context['report'] is '2':
            week_end_date = previous_day_date - timedelta(7)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            feedback_query = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                  feedback_date__range=(week_end_date,
                                                                        previous_day_date)
                                                  ).count()
            if shop_visit_count != 0:
                productivity = "{:.2f}%".format(float(shop_visit_count / feedback_query) * 100)
            else:
                productivity = str(00.00) + '%'
        # condition to check past month
        else:
            week_end_date = previous_day_date - timedelta(30)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            feedback_query = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()
            shop_visit_count = child_query.filter(day_beat_plan__in=date_beat_planning,
                                                  feedback_date__range=(
                                                      week_end_date, previous_day_date)
                                                  ).count()

            if shop_visit_count != 0:
                productivity = "{:.2f}%".format(float(shop_visit_count / feedback_query) * 100)
            else:
                productivity = str(00.00) + '%'
        return productivity

    def get_num_of_order(self, obj):
        """

        :param obj: object of shop user mapping
        :return: count of orders
        """
        # condition to check today
        if self._context['report'] is '0':
            order_count = Order.objects.filter(ordered_by=obj.employee, created_at__date=datetime.today()).count()

        # condition to check past day
        elif self._context['report'] is '1':
            previous_day_date = datetime.today() - timedelta(days=1)
            # previous_day_date = datetime.today()
            order_count = Order.objects.filter(ordered_by=obj.employee, created_at__date=previous_day_date).count()

        # condition to check past week
        elif self._context['report'] is '2':
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(7)
            order_count = Order.objects.filter(ordered_by=obj.employee, created_at__date__range=(
                week_end_date, previous_day_date)).count()
        # condition to check past month
        else:
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(30)
            order_count = Order.objects.filter(ordered_by=obj.employee, created_at__date__range=(
                week_end_date, previous_day_date)).count()

        return order_count

    def get_order_amount(self, obj):
        """

        :param obj: object of shop user mapping
        :return: total amount of order
        """
        # condition for today
        if self._context['report'] is '0':
            order_object = Order.objects.filter(ordered_by=obj.employee, created_at__date=datetime.today())
            # for order in order_object:
            try:
                payment_object = Payment.objects.filter(order_id__in=order_object)
                if payment_object.exists():
                    total_amount = round(payment_object.aggregate(Sum('paid_amount'))['paid_amount__sum'])
                else:
                    total_amount = 0
            except:
                total_amount = 0

        # condition to check past day
        elif self._context['report'] is '1':
            previous_day_date = datetime.today() - timedelta(days=1)
            # previous_day_date = datetime.today()
            order_object = Order.objects.filter(ordered_by=obj.employee, created_at__date=previous_day_date)
            # for order in order_object:
            try:
                payment_object = Payment.objects.filter(order_id__in=order_object)
                if payment_object.exists():
                    total_amount = round(payment_object.aggregate(Sum('paid_amount'))['paid_amount__sum'])
                else:
                    total_amount = 0
            except:
                total_amount = 0

        # condition to check past week
        elif self._context['report'] is '2':
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(7)
            order_object = Order.objects.filter(ordered_by=obj.employee, created_at__date__range=(
                week_end_date, previous_day_date))
            # for order in order_object:
            try:
                payment_object = Payment.objects.filter(order_id__in=order_object)
                if payment_object.exists():
                    total_amount = round(payment_object.aggregate(Sum('paid_amount'))['paid_amount__sum'])
                else:
                    total_amount = 0
            except:
                total_amount = 0

        # condition to check past month
        else:
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(30)
            order_object = Order.objects.filter(ordered_by=obj.employee, created_at__date__range=(
                week_end_date, previous_day_date))
            # for order in order_object:
            try:
                payment_object = Payment.objects.filter(order_id__in=order_object)
                if payment_object.exists():
                    total_amount = round(payment_object.aggregate(Sum('paid_amount'))['paid_amount__sum'])
                else:
                    total_amount = 0
            except:
                total_amount = 0

        return total_amount

    def get_inactive_shop_mapped(self, obj):
        """
        :param obj: object of shop user mapping
        :return: count of inactive shop map
        """
        previous_day_date = datetime.today() - timedelta(days=1)
        # previous_day_date = datetime.today()
        base_query = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee, is_active=False)

        # condition to check today
        if self._context['report'] is '0':
            date_beat_planning = base_query.filter(next_plan_date=datetime.today().date())
            inactive_shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        # condition to check past day
        elif self._context['report'] is '1':
            date_beat_planning = base_query.filter(next_plan_date=previous_day_date.date())
            inactive_shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        # condition to check past week
        elif self._context['report'] is '2':
            week_end_date = previous_day_date - timedelta(7)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            inactive_shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        # condition to check past month
        else:
            week_end_date = previous_day_date - timedelta(30)
            date_beat_planning = base_query.filter(next_plan_date__range=(week_end_date, previous_day_date))
            inactive_shop_map_count = ExecutiveFeedback.objects.filter(day_beat_plan__in=date_beat_planning).count()

        return inactive_shop_map_count

    class Meta:
        """ Meta class """
        model = ShopUserMapping
        fields = ('id', 'executive_name', 'executive_id', 'executive_contact_number', 'shop_mapped', 'shop_visited', 'productivity', 'num_of_order', 'order_amount', 'inactive_shop_mapped')

class FeedbackCreateSerializers(serializers.ModelSerializer):
    """
    Applied Sales Executive Feedback
    """
    day_beat_plan = serializers.SlugRelatedField(queryset=DayBeatPlanning.objects.all(), slug_field='id', required=True)
    executive_feedback = serializers.CharField(required=True, max_length=1)
    feedback_date = serializers.DateField(required=True)
    latitude = serializers.DecimalField(decimal_places=15, max_digits=30, required=True)
    longitude = serializers.DecimalField(decimal_places=15, max_digits=30, required=True)

    class Meta:
        """
        Applied executive feedback create meta class
        """
        model = ExecutiveFeedback
        fields = ('id', 'day_beat_plan', 'executive_feedback', 'feedback_date', 'feedback_time', 'created_at', 'modified_at', 'latitude', 'longitude')

    def create(self, validated_data):
        """

        :param validated_data: data which comes from post method
        :return: instance otherwise error message
        """
        # validated_data['feedback_date'] = datetime.today().strftime("%Y-%m-%d")
        # condition to check same reference of Day Beat Plan with same date is exist or not
        executive_feedback = ExecutiveFeedback.objects.filter(day_beat_plan=validated_data['day_beat_plan'])
        if executive_feedback.exists():
            # create instance of Executive Feedback
            executive_feedback.update(executive_feedback=validated_data['executive_feedback'],
                                      feedback_date=validated_data['feedback_date'],
                                      feedback_time=datetime.now().time(),
                                      latitude=validated_data.get('latitude', None),
                                      longitude=validated_data.get('longitude', None))

            # condition to check if executive apply "Could Not Visit" for less than equal to 5 within the same date
            # then assign next visit date and beat plan date accordingly
            # day_beat_plan = DayBeatPlanning.objects.filter(id=validated_data['day_beat_plan'].id)
            # if (ExecutiveFeedback.objects.filter(executive_feedback=5, feedback_date=validated_data['feedback_date']
            #                                      ).count() <= 5) and executive_feedback[0].executive_feedback == '5':
            #     if day_beat_plan[0].shop_category == "P1":
            #         next_visit_date = validated_data['feedback_date'] + timedelta(days=1)
            #         beat_plan_date = day_beat_plan[0].beat_plan_date + timedelta(days=7)
            #         temp_status = True
            #     elif day_beat_plan[0].shop_category == "P2":
            #         next_visit_date = validated_data['feedback_date'] + timedelta(days=2)
            #         beat_plan_date = day_beat_plan[0].beat_plan_date + timedelta(days=14)
            #         temp_status = True
            #     else:
            #         next_visit_date = validated_data['feedback_date'] + timedelta(days=3)
            #         beat_plan_date = day_beat_plan[0].beat_plan_date + timedelta(days=28)
            #         temp_status = True
            #
            # # condition to check if executive apply feedback which is not related to "Could Not Visit" and also
            # # check next visit date condition for rest of the feedback
            # else:
            #     if day_beat_plan[0].shop_category == "P1" and day_beat_plan[0].temp_status is False:
            #         next_visit_date = day_beat_plan[0].beat_plan_date + timedelta(days=7)
            #         beat_plan_date = next_visit_date
            #         temp_status = False
            #
            #     elif day_beat_plan[0].shop_category == "P2" and day_beat_plan[0].temp_status is False:
            #         next_visit_date = day_beat_plan[0].beat_plan_date + timedelta(days=14)
            #         beat_plan_date = next_visit_date
            #         temp_status = False
            #
            #     elif day_beat_plan[0].shop_category == "P3" and day_beat_plan[0].temp_status is False:
            #         next_visit_date = day_beat_plan[0].beat_plan_date + timedelta(days=28)
            #         beat_plan_date = next_visit_date
            #         temp_status = False
            #     else:
            #         next_visit_date = day_beat_plan[0].beat_plan_date
            #         beat_plan_date = next_visit_date
            #         temp_status = False

            # Create Data for next visit in Day Beat Planning
            # DayBeatPlanning.objects.get_or_create(shop_category=day_beat_plan[0].shop_category,
            #                                       next_plan_date=next_visit_date,
            #                                       beat_plan_date=beat_plan_date,
            #                                       shop=day_beat_plan[0].shop,
            #                                       beat_plan=day_beat_plan[0].beat_plan,
            #                                       temp_status=temp_status)

            # return executive feedback instance
            return executive_feedback[0]
        else:
            validated_data['feedback_time'] = datetime.now().time()
            return ExecutiveFeedback.objects.create(**validated_data)
            
        # return False

class ChoiceField(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'desc': self._choices[obj]}

class ShopBasicSerializer(serializers.ModelSerializer):
    shop = serializers.SerializerMethodField()

    def get_shop(self, obj):
        """
        :param obj: object of shop model
        :return: executive __str__()
        """
        return obj.__str__()

    class Meta:
        model = Shop
        ref_name = 'Shop Basic Serializer v1'
        fields = ('id', 'shop')


class PosShopUserMappingCreateSerializer(serializers.ModelSerializer):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    phone_number = serializers.CharField(validators=[phone_regex], max_length=10, required=True)
    user_type = ChoiceField(choices=USER_TYPE_CHOICES)
    is_delivery_person = serializers.BooleanField()

    class Meta:
        model = PosShopUserMapping
        fields = ('phone_number', 'user_type', 'is_delivery_person')

    def validate(self, attrs):
        try:
            user = User.objects.get(phone_number=attrs['phone_number'])
        except:
            raise serializers.ValidationError("User with given phone number not found")
        if PosShopUserMapping.objects.filter(shop=self.context.get('shop'), user=user).exists():
            raise serializers.ValidationError("User with given phone number already mapped to this shop")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.get(phone_number=validated_data['phone_number'])
        return PosShopUserMapping.objects.create(shop=self.context.get('shop'), user=user,
                                                 user_type=validated_data['user_type'],
                                                 created_by=self.context.get('created_by'),
                                                 is_delivery_person=validated_data['is_delivery_person'])


class PosShopUserMappingUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    user_type = serializers.ChoiceField(choices=['cashier', 'manager'], required=False)
    status = serializers.BooleanField(required=False)
    is_delivery_person = serializers.BooleanField(required=False)

    class Meta:
        model = PosShopUserMapping
        fields = ('id', 'user_type', 'status', 'is_delivery_person')

    def validate(self, attrs):
        if not PosShopUserMapping.objects.filter(id=attrs['id'], shop=self.context.get('shop')).exists():
            raise serializers.ValidationError("Invalid mapping ID")
        return attrs

    @transaction.atomic
    def update(self, instance_id, validated_data):
        mapping = PosShopUserMapping.objects.get(id=instance_id)
        mapping.user_type = validated_data['user_type'] if 'user_type' in validated_data else mapping.user_type
        mapping.status = validated_data['status'] if 'status' in validated_data else mapping.status
        mapping.is_delivery_person = validated_data['is_delivery_person'] if 'is_delivery_person' in validated_data else mapping.is_delivery_person
        mapping.save()

