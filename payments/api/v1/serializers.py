import traceback
import sys
import re

from django.db import transaction
from rest_framework import serializers

from retailer_to_sp.models import OrderedProduct
from payments.models import ShipmentPayment, PaymentMode, \
    Payment, OrderPayment, PaymentImage



class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"  


class PaymentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentImage
        fields = ('id','reference_image',)
        extra_kwargs = {
            'user_document_type': {'required': True},
            }

# class OrderPaymentSerializer(serializers.ModelSerializer):
#     parent_payment = PaymentSerializer()

#     class Meta:
#         model = OrderPayment
#         fields = "__all__"

class ShipmentPaymentSerializer(serializers.ModelSerializer):
    #paid_amount = serializers.DecimalField(default=0.0000, max_digits=20, decimal_places=4)
    payment_mode_name = serializers.CharField(max_length=50)
    reference_no = serializers.CharField(required=False)
    online_payment_type = serializers.CharField(required=False)
    paid_by = serializers.CharField(source='parent_order_payment.parent_payment.paid_by.phone_number', required=False)
    payment_screenshot = serializers.IntegerField(required=False)#source='parent_order_payment.parent_payment.payment_screenshot', required=False)
    #cash_payment = CashPaymentSerializer(fields=['paid_amount'])
    #online_payment = OnlinePaymentSerializer()
    class Meta:
        model = ShipmentPayment
        fields = ['description', 'paid_amount', 'payment_mode_name', 'reference_no', 
            'online_payment_type', 'paid_by', 'payment_screenshot'
            ]  #"__all__"



class ShipmentPaymentSerializer2(serializers.Serializer):
    #paid_amount = serializers.DecimalField(default=0.0000, max_digits=20, decimal_places=4)
    payment_data = ShipmentPaymentSerializer(many=True)
    class Meta:
        fields = ['payment_data', 'shipment', 'paid_by'
            ]  #"__all__"

    def validate(self, data):
        initial_data = self.initial_data
        shipment = initial_data.get('shipment', None)
        paid_by = initial_data.get('paid_by', None)
        if not OrderedProduct.objects.filter(pk=shipment).exists():
            raise serializers.ValidationError("Shipment not found!")
        if not UserWithName.objects.filter(phone_number=paid_by).exists():
            raise serializers.ValidationError("Paid by User not found!")  
        payment_data = initial_data.get('payment_data', None) 
        s = ShipmentPaymentSerializer(initial_data=payment_data)


class ReadShipmentPaymentSerializer(serializers.ModelSerializer):
    #parent_order_payment = OrderPaymentSerializer()
    payment_mode_name = serializers.SerializerMethodField()
    reference_no = serializers.SerializerMethodField()
    payment_screenshot = serializers.SerializerMethodField()
    online_payment_type = serializers.SerializerMethodField()
    paid_by = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentPayment
        fields = ['description', 'paid_amount', 'payment_mode_name', 'reference_no', 
            'shipment', 'online_payment_type', 'payment_screenshot', 'paid_by'
            ] 

    def get_paid_by(self, obj):
        return obj.parent_order_payment.parent_payment.paid_by.__str__()

    def get_payment_mode_name(self, obj):
        return obj.parent_order_payment.parent_payment.payment_mode_name

    def get_online_payment_data(self, obj):
        if self.get_payment_mode_name(obj) == "online_payment":
            parent_payment = obj.parent_order_payment.parent_payment
            return parent_payment.reference_no, parent_payment.online_payment_type,\
                parent_payment.payment_screenshot

    def get_reference_no(self, obj):
        if self.get_payment_mode_name(obj) == "online_payment":
            payment_data = self.get_online_payment_data(obj)
            return payment_data[0]
            #return obj.parent_order_payment.parent_payment.reference_no

    def get_payment_screenshot(self, obj):
        if self.get_payment_mode_name(obj) == "online_payment":
            payment_data = self.get_online_payment_data(obj)
            if payment_data[2]:
                return payment_data[2].url

    def get_online_payment_type(self, obj):
        if self.get_payment_mode_name(obj) == "online_payment":
            payment_data = self.get_online_payment_data(obj)
            return payment_data[1]
            #return obj.parent_order_payment.parent_payment.online_payment_type
         

class OrderPaymentSerializer(serializers.ModelSerializer):
    payment_mode_name = serializers.CharField(max_length=50)
    reference_no = serializers.CharField(required=False)
    online_payment_type = serializers.CharField(required=False)
    paid_by = serializers.CharField(source='parent_payment.paid_by.phone_number', required=False)
    payment_screenshot = serializers.FileField(source='parent_payment.payment_screenshot', required=False)

    class Meta:
        model = OrderPayment
        fields = ['description', 'paid_amount', 'payment_mode_name', 'reference_no', 
            'online_payment_type', 'paid_by', 'payment_screenshot'
            ]  #"__all__"

    def validate(self, data):
        initial_data = self.initial_data

        for item in initial_data:
            if item.get('payment_mode_name') is None:
                raise serializers.ValidationError("Payment mode name is required!")
            if item['payment_mode_name'] == "online_payment":
                if item.get('reference_no') is None:
                    raise serializers.ValidationError("Reference number is required!!!!")
                    # raise ValidationError("Reference number is required") 
                if item.get('online_payment_type') is None:
                    raise serializers.ValidationError("Online payment type is required!!!!")

        return data    


class OrderPaymentSerializer1(serializers.ModelSerializer):
    payment_mode_name = serializers.SerializerMethodField()
    reference_no = serializers.SerializerMethodField()
    online_payment_type = serializers.SerializerMethodField()
    paid_by = serializers.SerializerMethodField()

    class Meta:
        model = OrderPayment
        fields = ['description', 'paid_amount', 'payment_mode_name', 'reference_no', 
            'order', 'online_payment_type', 'paid_by'
            ] 

    def get_paid_by(self, obj):
        return obj.parent_payment.paid_by

    def get_payment_mode_name(self, obj):
        return obj.parent_payment.payment_mode_name

    def get_online_payment_data(self, obj):
        if self.get_payment_mode_name(obj) == "online_payment":
            parent_payment = obj.parent_payment
            return parent_payment.reference_no, parent_payment.online_payment_type

    def get_reference_no(self, obj):
        if self.get_payment_mode_name(obj) == "online_payment":
            reference_no, _ = self.get_online_payment_data(obj)
            return reference_no

    def get_online_payment_type(self, obj):
        if self.get_payment_mode_name(obj) == "online_payment":
            _, online_payment_type = self.get_online_payment_data(obj)
            return online_payment_type