import traceback
import sys
import re

from django.core.validators import RegexValidator
from django.db import transaction
from rest_framework import serializers

from retailer_to_sp.models import OrderedProduct, Trip
from retailer_to_sp.views import update_shipment_status_with_id
from retailer_to_sp.api.v1.views import update_trip_status    


from payments.models import (
    ShipmentPayment, PaymentMode, Payment, OrderPayment, PaymentImage
)

from accounts.api.v1.serializers import UserDocumentSerializer
from accounts.models import UserDocument


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = ['paid_amount', 'payment_mode_name', 'reference_no',
                  'online_payment_type', 'description']
        extra_kwargs = {
            'paid_amount': {'required': True},
            'payment_mode_name': {'required': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paid_amount'].error_messages['required'] = "Please enter paid amount"
        self.fields['payment_mode_name'].error_messages['required'] = "Please enter payment mode name"

    def validate(self, data):
        if data.get('payment_mode_name', None) == 'online_payment':
            if not data.get('reference_no', None):
                raise serializers.ValidationError({'reference_no': 'Please enter Reference No.'})
            if not data.get('online_payment_type', None):
                raise serializers.ValidationError({'online_payment_type': 'Please enter online payment type'})                
        return data

    def validate_reference_no(self, data):
        if not re.match("^[a-zA-Z0-9_]*$", data):
            raise serializers.ValidationError('Referece number cannot have special character.')

        if Payment.objects.filter(payment_mode_name='online_payment',
                                  reference_no=data).exists():
            raise serializers.ValidationError('This referece number already exists.')
        return data


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


class ShipmentPaymentSerializer(serializers.Serializer):
    shipment = serializers.IntegerField()
    trip = serializers.IntegerField()
    amount_collected = serializers.FloatField()
    return_reason = serializers.ChoiceField(
        choices=OrderedProduct.RETURN_REASON, required=False)
    payment_data = PaymentSerializer(many=True)
    user_documents = UserDocumentSerializer(many=True, required=False)
    pan_uploaded = serializers.BooleanField(default=False)

    class Meta:
        fields = ['shipment', 'trip', 'amount_collected', 'payment_data',
                  'user_documents', 'return_reason', 'pan_uploaded']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['amount_collected'].error_messages['required'] = "Please enter cash to be collected"
        self.fields['trip'].error_messages['required'] = "Trip ID is required"
        self.fields['shipment'].error_messages['required'] = "Shipment ID is required"

    def validate_shipment(self, data):
        try:
            shipment = OrderedProduct.objects.get(id=data)
        except:
            raise serializers.ValidationError('Shipment ID is not valid.')
        else:
            self.context['shipment'] = shipment
            self.context['order'] = shipment.order
            self.context['paid_by'] = shipment.order.buyer_shop.shop_owner
            self.context['processed_by'] = self.context['request'].user
            self.context['cash_to_be_collected'] = shipment.cash_to_be_collected()
            return data

    def validate_trip(self, data):
        try:
            trip = Trip.objects.get(id=data)
        except:
            raise serializers.ValidationError('Trip ID is not valid.')
        else:
            return data

    def validate_payment_data(self, data):
        if not data:
            raise serializers.ValidationError('Please enter payment details')
        if (sum([i.get('paid_amount') for i in data]) !=
                self.context.get('cash_to_be_collected')):
            raise serializers.ValidationError('Sum of paid amount must be equal to amount collected')
        return data



    def is_pan_required(self, data):
        payment_data = data.get('payment_data')
        cash_amount = sum([i.get('paid_amount') for i in payment_data
                            if i.get('payment_mode_name') == 'cash_payment'])
        user_pan_card = self.context['paid_by'].user_documents.\
            filter(user_document_type='pc').exists()
        if int(cash_amount) >= 10000 and not user_pan_card:
            return True
        return False

    def validate(self, data):
        cash_collected = data.get('amount_collected')
        cash_to_be_collected = self.context.get('cash_to_be_collected')

        if int(cash_collected) != int(cash_to_be_collected):
            raise serializers.ValidationError(
                'Amount collected and amount to be collected must be equal ({})'.
                format(int(cash_to_be_collected)))

        if self.is_pan_required(data) and data.get('pan_uploaded') and not data.get('user_documents'):
            self.context['is_pan_required'] = True
            raise serializers.ValidationError('Please update PAN details')
        return data

    def create(self, validated_data):
        created_data_dict = {
            'shipment': validated_data.get('shipment'),
            'trip': validated_data.get('trip'),
            'return_reason': validated_data.get('return_reason', None),
            'amount_collected': validated_data.get('amount_collected'),
            'pan_uploaded': validated_data.get('pan_uploaded')
        }
        created_data_dict['user_documents'] = []
        created_data_dict['payment_data'] = []

        user_documents = validated_data.get('user_documents', None)
        return_reason = validated_data.get('return_reason', None)
        payments = validated_data.get('payment_data')

        try:
            with transaction.atomic():
                # shipment return reason
                if return_reason:
                    shipment = self.context.get('shipment')
                    shipment.return_reason = return_reason
                    shipment.save()

                # creating user documents
                for user_document in user_documents:
                    user_document_obj = UserDocument.objects.create(
                        user=self.context.get('paid_by'), **user_document)
                    created_data_dict['user_documents'].append(user_document_obj)

                # creating payments
                for payment_data in payments:
                    payment = Payment.objects.create(
                        paid_by=self.context.get('paid_by'),
                        processed_by=self.context.get('processed_by'),
                        **payment_data
                    )
                    created_data_dict['payment_data'].append(payment)
                    # create order payment
                    order_payment = OrderPayment.objects.create(
                        paid_amount=payment_data.get('paid_amount'),
                        parent_payment=payment,
                        order=self.context.get('order'),
                        created_by=self.context.get('processed_by'),
                        updated_by=self.context.get('processed_by')
                    )

                    # create shipment payment
                    shipment_payment = ShipmentPayment.objects.create(
                        paid_amount=payment_data.get('paid_amount'),
                        parent_order_payment=order_payment,
                        shipment=self.context.get('shipment'),
                        created_by=self.context.get('processed_by'),
                        updated_by=self.context.get('processed_by')
                    )

                # update shipment and trip status
                update_shipment_status_with_id(self.context.get('shipment'))
                update_trip_status(validated_data.get('trip'))

        except Exception as e:
            raise serializers.ValidationError(e)

        return created_data_dict


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