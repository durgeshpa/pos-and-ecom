import traceback
import sys
import re

from django.db import transaction
from rest_framework import serializers

from retailer_to_sp.models import OrderedProduct
from payments.models import ShipmentPayment, CashPayment, OnlinePayment, PaymentMode, \
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


class CashPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashPayment
        fields = "__all__"


class OnlinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePayment
        fields = "__all__"
        


class ShipmentPaymentSerializer(serializers.ModelSerializer):
    #paid_amount = serializers.DecimalField(default=0.0000, max_digits=20, decimal_places=4)
    payment_mode_name = serializers.CharField(max_length=50)
    reference_no = serializers.CharField(required=False)
    online_payment_type = serializers.CharField(required=False)
    paid_by = serializers.CharField(source='parent_order_payment.parent_payment.paid_by.phone_number', required=False)
    payment_screenshot = serializers.IntegerField()#source='parent_order_payment.parent_payment.payment_screenshot', required=False)
    #cash_payment = CashPaymentSerializer(fields=['paid_amount'])
    #online_payment = OnlinePaymentSerializer()
    class Meta:
        model = ShipmentPayment
        fields = ['description', 'paid_amount', 'payment_mode_name', 'reference_no', 
            'online_payment_type', 'paid_by', 'payment_screenshot'
            ]  #"__all__"

    def validate(self, data):
        initial_data = self.initial_data
        #import pdb; pdb.set_trace()

        for item in initial_data:
            if item.get('paid_amount') is None:
                raise serializers.ValidationError("Paid amount is required!")
            if item.get('payment_mode_name') is None:
                raise serializers.ValidationError("Payment mode name is required!")
            if item['payment_mode_name'] == "online_payment":
                if item.get('reference_no') is None:
                    raise serializers.ValidationError("Reference number is required!")
                    # raise ValidationError("Reference number is required") 
                else:
                    payment = Payment.objects.filter(reference_no = item['reference_no'])
                    if payment.exists():
                        raise serializers.ValidationError('This referece number already exists.') 

                if item.get('online_payment_type') is None:
                    raise serializers.ValidationError("Online payment type is required!")

                reference_no = item.get('reference_no', None)#['reference_no']
                if reference_no:
                    if not re.match("^[a-zA-Z0-9_]*$", reference_no):
                        raise serializers.ValidationError('Referece number can not have special character!')
        return data    

    # def create(self, validated_data):
        
    #     # try:
    #     #with transaction.atomic():
    #     #import pdb; pdb.set_trace()
    #     shipment = validated_data.pop('shipment', None)
    #     paid_amount = validated_data.pop('paid_amount', None)
    #     payment_mode_name = validated_data.pop('payment_mode_name', None)
        
    #     reference_no = validated_data.pop('reference_no', None)
    #     online_payment_type = validated_data.pop('online_payment_type', None)
    #     description = validated_data.pop('description', None)

    #     # create payment
    #     payment = Payment.objects.create(
    #         paid_amount = paid_amount,
    #         payment_mode_name = payment_mode_name,
    #         )
    #     if payment_mode_name == "online_payment":
    #         # if reference_no is None:
    #         #     raise serializers.ValidationError("Reference number is required!")
    #         #     # raise ValidationError("Reference number is required") 
    #         # if online_payment_type is None:
    #         #     raise serializers.ValidationError("Online payment type is required!")

    #         payment.reference_no = reference_no
    #         payment.online_payment_type = online_payment_type
    #     payment.save()

    #     # create order payment
    #     shipment = OrderedProduct.objects.get(pk=shipment)
    #     order_payment = OrderPayment.objects.create(
    #         paid_amount = paid_amount,
    #         parent_payment = payment,
    #         order = shipment.order
    #         )
        
    #     # create shipment payment
    #     shipment_payment = ShipmentPayment.objects.create(
    #         paid_amount = paid_amount,
    #         parent_order_payment = order_payment,
    #         shipment = shipment
    #         )
        
    #     return shipment_payment
    #     # except Exception as e:
    #     #     print (traceback.format_exc(sys.exc_info()))
    #     #     raise serializers.ValidationError(e.message)        
    



class ShipmentPaymentSerializer2(serializers.Serializer):
    #paid_amount = serializers.DecimalField(default=0.0000, max_digits=20, decimal_places=4)
    payment_data = ShipmentPaymentSerializer(many=True)
    class Meta:
        fields = ['payment_data', 'shipment', 'paid_by'
            ]  #"__all__"

    def validate(self, data):
        initial_data = self.initial_data
        #import pdb; pdb.set_trace() 
        shipment = initial_data.get('shipment', None)
        paid_by = initial_data.get('paid_by', None)
        if not OrderedProduct.objects.filter(pk=shipment).exists():
            raise serializers.ValidationError("Shipment not found!")
        if not UserWithName.objects.filter(phone_number=paid_by).exists():
            raise serializers.ValidationError("Paid by User not found!")  
        payment_data = initial_data.get('payment_data', None) 
        s = ShipmentPaymentSerializer(initial_data=payment_data)


class ShipmentPaymentSerializer1(serializers.ModelSerializer):
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
         
    # def validate(self, data):
    #     initial_data = self.initial_data
    #     reference_no = initial_data['reference_no']
    #     if not re.match("^[a-zA-Z0-9_]*$", reference_no):
    #         raise serializers.ValidationError('Referece number can not have special character!')
    #     return initial_data  

    # def create(self, validated_data):
    #     # import pdb; pdb.set_trace()
    #     parent_order_payment = validated_data.pop('parent_order_payment')
    #     shipment = validated_data.pop('shipment')
    #     paid_amount = validated_data.pop('paid_amount')
    #     description = validated_data.pop('description')
    #     try:
    #         with transaction.atomic(): #for roll back if any exception occur
    #             # if payment data contains id then update else create
    #             parent_order_payment_inst, created = OrderPayment.objects.update_or_create(**parent_order_payment)
    #             parent_order_payment_inst.save()
    #             # create or update shipment payment instance
    #             shipment_payment, created = ShipmentPayment.objects.update_or_create(
    #                 parent_order_payment=parent_order_payment_inst,
    #                 shipment = shipment)
    #             shipment_payment.paid_amount = paid_amount
    #             shipment_payment.description = description
    #             shipment_payment.save()
    #             return shipment_payment
    #     except Exception as e:
    #         raise serializers.ValidationError(str(e))


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