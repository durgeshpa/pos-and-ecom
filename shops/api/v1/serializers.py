import re
import datetime
from rest_framework import serializers
from datetime import datetime, timedelta

from shops.models import (RetailerType, ShopType, Shop, ShopPhoto,
    ShopRequestBrand, ShopDocument, ShopUserMapping, SalesAppVersion, ShopTiming,
    FavouriteProduct, DayBeatPlanning, ExecutiveFeedback
)
from django.contrib.auth import get_user_model
from accounts.api.v1.serializers import UserSerializer,GroupSerializer
from retailer_backend.validators import MobileNumberValidator
from rest_framework import validators
from retailer_to_sp.models import Order
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
        return executive_feedback

    class Meta:
        """ Meta class """
        model = ExecutiveFeedback
        fields = ('id', 'day_beat_plan', 'executive_feedback', 'executive_feedback_value', 'feedback_date',)


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
        serializer = FeedBackSerializer(obj.day_beat_plan, many=True).data
        return serializer

    class Meta:
        """ Meta class """
        model = DayBeatPlanning
        fields = ('day_beat_plan', 'beat_plan', 'shop_category', 'beat_plan_date', 'next_plan_date', 'temp_status',
                  'shop', 'feedback')


class ExecutiveReportSerializer(serializers.ModelSerializer):
    """
    This is Serializer to ger Report for Sales Executive
    """
    executive_name = serializers.SerializerMethodField()
    shop_mapped = serializers.SerializerMethodField()
    shop_visited = serializers.SerializerMethodField()
    productivity = serializers.SerializerMethodField()
    num_of_order = serializers.SerializerMethodField()
    order_amount = serializers.SerializerMethodField()

    def get_executive_name(self, obj):
        """

        :param obj: object of shop user mapping
        :return: executive first name
        """
        return obj.employee.first_name

    def get_shop_mapped(self, obj):
        """

        :param obj: object of shop user mapping
        :return: count of shop map
        """
        # condition to check past day
        if self._context['report'] is '1':
            previous_day_date = datetime.today() - timedelta(days=1)
            # shop_map_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                 next_plan_date=previous_day_date,
            #                                                 beat_plan__status=True).count()
            shop_map_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                            next_plan_date=previous_day_date.date()).distinct(
                'shop_category', 'next_plan_date').count()
        # condition to check past week
        elif self._context['report'] is '2':
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date-timedelta(7)
            # shop_map_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                 next_plan_date__range=(week_end_date,
            #                                                                        previous_day_date),
            #                                                 beat_plan__status=True).count()
            shop_map_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                            next_plan_date__range=(week_end_date,
                                                                                   previous_day_date)).distinct(
                'shop_category', 'next_plan_date').count()
        # condition to check past month
        else:
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(30)
            # shop_map_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                 next_plan_date__range=(week_end_date,
            #                                                                        previous_day_date),
            #                                                 beat_plan__status=True).count()
            shop_map_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                            next_plan_date__range=(week_end_date,
                                                                                   previous_day_date)).distinct(
                'shop_category', 'next_plan_date').count()
        return shop_map_count

    def get_shop_visited(self, obj):
        """

        :param obj: object of shop user mapping
        :return: count of shop visit
        """
        # condition to check past day
        if self._context['report'] is '1':
            previous_day_date = datetime.today() - timedelta(days=1)
            shop_visit_count = 0
            # date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                     next_plan_date=previous_day_date,
            #                                                     beat_plan__status=True)

            date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                                next_plan_date=previous_day_date)
            for date_beat in date_beat_planning:
                shop_visited = ExecutiveFeedback.objects.filter(day_beat_plan=date_beat,
                                                                feedback_date=previous_day_date).count()
                shop_visit_count = shop_visit_count+shop_visited

        # condition to check past week
        elif self._context['report'] is '2':
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(7)
            shop_visit_count = 0
            # date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                     next_plan_date__range=(week_end_date,
            #                                                                            previous_day_date),
            #                                                     beat_plan__status=True)
            date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                                next_plan_date__range=(week_end_date,
                                                                                       previous_day_date))
            for date_beat in date_beat_planning:
                shop_visited = ExecutiveFeedback.objects.filter(day_beat_plan=date_beat,
                                                                feedback_date__range=(week_end_date,
                                                                                      previous_day_date)).count()
                shop_visit_count = shop_visit_count + shop_visited
        # condition to check past week
        else:
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(30)
            shop_visit_count = 0
            # date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                     next_plan_date__range=(
            #                                                         week_end_date, previous_day_date),
            #                                                     beat_plan__status=True)

            date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                                next_plan_date__range=(
                                                                    week_end_date, previous_day_date))
            for date_beat in date_beat_planning:
                shop_visited = ExecutiveFeedback.objects.filter(day_beat_plan=date_beat,
                                                                feedback_date__range=(
                                                                    week_end_date, previous_day_date)).count()
                shop_visit_count = shop_visit_count + shop_visited

        return shop_visit_count

    def get_productivity(self, obj):
        """

        :param obj: object of shop user mapping
        :return: productivity of sales executive
        """
        # condition to check past day
        if self._context['report'] is '1':
            previous_day_date = datetime.today() - timedelta(days=1)
            # shop_mapped_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                    next_plan_date=previous_day_date,
            #                                                    beat_plan__status=True).count()
            shop_mapped_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                               next_plan_date=previous_day_date.date()).distinct(
                'shop_category', 'next_plan_date').count()
            shop_visit_count = 0
            # date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                     next_plan_date=previous_day_date,
            #                                                     beat_plan__status=True)

            date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                                next_plan_date=previous_day_date)

            for date_beat in date_beat_planning:
                shop_visited = ExecutiveFeedback.objects.filter(day_beat_plan=date_beat,
                                                                feedback_date=previous_day_date).count()
                shop_visit_count = shop_visit_count + shop_visited

            if shop_visit_count != 0:
                productivity = str(round(shop_visit_count / shop_mapped_count, 4) * 100) + '%'
            else:
                productivity = str(00.00) + '%'
        # condition to check past week
        elif self._context['report'] is '2':
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(7)
            # shop_mapped_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                    next_plan_date__range=(week_end_date,
            #                                                                           previous_day_date),
            #                                                    beat_plan__status=True).count()

            shop_mapped_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                            next_plan_date__range=(week_end_date,
                                                                                   previous_day_date)).distinct(
                'shop_category', 'next_plan_date').count()

            shop_visit_count = 0
            # date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                     next_plan_date__range=(week_end_date,
            #                                                                            previous_day_date),
            #                                                     beat_plan__status=True)

            date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                                next_plan_date__range=(week_end_date,
                                                                                       previous_day_date))
            for date_beat in date_beat_planning:
                shop_visited = ExecutiveFeedback.objects.filter(day_beat_plan=date_beat,
                                                                feedback_date__range=(week_end_date,
                                                                                      previous_day_date)).count()
                shop_visit_count = shop_visit_count + shop_visited

            if shop_visit_count != 0:
                productivity = str(round(shop_visit_count / shop_mapped_count, 4) * 100) + '%'
            else:
                productivity = str(00.00) + '%'
        # condition to check past month
        else:
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(30)
            # shop_mapped_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                    next_plan_date__range=(week_end_date,
            #                                                                           previous_day_date),
            #                                                    beat_plan__status=True).count()

            shop_mapped_count = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                            next_plan_date__range=(week_end_date,
                                                                                   previous_day_date)).distinct(
                'shop_category', 'next_plan_date').count()

            shop_visit_count = 0
            # date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
            #                                                     next_plan_date__range=(week_end_date,
            #                                                                            previous_day_date),
            #                                                     beat_plan__status=True)

            date_beat_planning = DayBeatPlanning.objects.filter(beat_plan__executive=obj.employee,
                                                                next_plan_date__range=(week_end_date,
                                                                                       previous_day_date))

            for date_beat in date_beat_planning:
                shop_visited = ExecutiveFeedback.objects.filter(day_beat_plan=date_beat, feedback_date__range=(
                    week_end_date, previous_day_date)).count()
                shop_visit_count = shop_visit_count + shop_visited

            if shop_visit_count != 0:
                productivity = str(round(shop_visit_count / shop_mapped_count, 4) * 100) + '%'
            else:
                productivity = str(00.00) + '%'
        return productivity

    def get_num_of_order(self, obj):
        """

        :param obj: object of shop user mapping
        :return: count of orders
        """
        # condition to check past day
        if self._context['report'] is '1':
            previous_day_date = datetime.today() - timedelta(days=1)
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
        # condition to check past day
        if self._context['report'] is '1':
            previous_day_date = datetime.today() - timedelta(days=1)
            order_object = Order.objects.filter(ordered_by=obj.employee, created_at__date=previous_day_date)
            total_amount = 0
            for order in order_object:
                total_amount = round(total_amount + order.total_mrp)

        # condition to check past week
        elif self._context['report'] is '2':
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(7)
            order_object = Order.objects.filter(ordered_by=obj.employee, created_at__date__range=(
                week_end_date, previous_day_date))
            total_amount = 0
            for order in order_object:
                total_amount = round(total_amount + order.total_mrp)

        # condition to check past month
        else:
            previous_day_date = datetime.today() - timedelta(days=1)
            week_end_date = previous_day_date - timedelta(30)
            order_object = Order.objects.filter(ordered_by=obj.employee, created_at__date__range=(
                week_end_date, previous_day_date))
            total_amount = 0
            for order in order_object:
                total_amount = round(total_amount + order.total_mrp)

        return total_amount

    class Meta:
        """ Meta class """
        model = ShopUserMapping
        fields = ('id', 'executive_name', 'shop_mapped', 'shop_visited', 'productivity', 'num_of_order',
                  'order_amount')


class FeedbackCreateSerializers(serializers.ModelSerializer):
    """
    Applied Sales Executive Feedback
    """
    day_beat_plan = serializers.SlugRelatedField(queryset=DayBeatPlanning.objects.all(), slug_field='id', required=True)
    executive_feedback = serializers.CharField(required=True, max_length=1)
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
        # validated_data['feedback_date'] = datetime.today().strftime("%Y-%m-%d")
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
                day_beat_plan = DayBeatPlanning.objects.filter(id=validated_data['day_beat_plan'].id)
                if (ExecutiveFeedback.objects.filter(executive_feedback=5, feedback_date=validated_data['feedback_date']
                                                     ).count() <= 5) and instance.executive_feedback == '5':
                    if day_beat_plan[0].shop_category == "P1":
                        next_visit_date = validated_data['feedback_date'] + timedelta(days=1)
                        beat_plan_date = day_beat_plan[0].beat_plan_date + timedelta(days=7)
                        temp_status = True
                    elif day_beat_plan[0].shop_category == "P2":
                        next_visit_date = validated_data['feedback_date'] + timedelta(days=2)
                        beat_plan_date = day_beat_plan[0].beat_plan_date + timedelta(days=14)
                        temp_status = True
                    else:
                        next_visit_date = validated_data['feedback_date'] + timedelta(days=3)
                        beat_plan_date = day_beat_plan[0].beat_plan_date + timedelta(days=28)
                        temp_status = True

                # condition to check if executive apply feedback which is not related to "Could Not Visit" and also
                # check next visit date condition for rest of the feedback
                else:
                    if day_beat_plan[0].shop_category == "P1" and day_beat_plan[0].temp_status is False:
                        next_visit_date = day_beat_plan[0].beat_plan_date + timedelta(days=7)
                        beat_plan_date = next_visit_date
                        temp_status = False

                    elif day_beat_plan[0].shop_category == "P2" and day_beat_plan[0].temp_status is False:
                        next_visit_date = day_beat_plan[0].beat_plan_date + timedelta(days=14)
                        beat_plan_date = next_visit_date
                        temp_status = False

                    elif day_beat_plan[0].shop_category == "P3" and day_beat_plan[0].temp_status is False:
                        next_visit_date = day_beat_plan[0].beat_plan_date + timedelta(days=28)
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
            # return False
            return False
        # return False
        return False
