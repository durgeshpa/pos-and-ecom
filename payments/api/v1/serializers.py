import traceback
import sys
import re

from django.db import transaction
from rest_framework import serializers

from payments.models import ShipmentPayment, CashPayment, OnlinePayment, PaymentMode


class CashPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashPayment
        fields = "__all__"


class OnlinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePayment
        fields = "__all__"
        

class ShipmentPaymentSerializer(serializers.ModelSerializer):
    cash_amount = serializers.DecimalField(default=0.0000, max_digits=20, decimal_places=4)
    payment_mode = serializers.CharField(allow_blank=True)
    reference_no = serializers.CharField(default="")
    online_amount = serializers.DecimalField(default=0.0000, max_digits=20, decimal_places=4)

    #cash_payment = CashPaymentSerializer(fields=['paid_amount'])
    #online_payment = OnlinePaymentSerializer()
    class Meta:
        model = ShipmentPayment
        fields = ['description', 'cash_amount', 'payment_mode', 'reference_no', 'online_amount']  #"__all__"

    def validate(self, data):
        initial_data = self.initial_data
        reference_no = initial_data['reference_no']
        if not re.match("^[a-zA-Z0-9_]*$", reference_no):
            raise serializers.ValidationError('Referece number can not have special character!')
        return initial_data     

    def update(self, instance, validated_data):
        
        try:
            with transaction.atomic():
                #import pdb; pdb.set_trace()
                cash_payment = validated_data.pop('cash_amount', None)

                online_payment_mode = validated_data.pop('payment_mode', None)
                reference_no = validated_data.pop('reference_no', None)
                online_payment = validated_data.pop('online_amount', None)
                description = validated_data.pop('description', None)

                if cash_payment:
                    _cash_payment = CashPayment.objects.get(payment=instance)
                    _cash_payment.paid_amount = float(cash_payment) #.paid_amount
                    _cash_payment.save()

                if online_payment_mode:
                    _payment_mode, created = PaymentMode.objects.get_or_create(
                        payment=instance, payment_mode_name="online_payment")

                    _online_payment, created = OnlinePayment.objects.get_or_create(payment=instance)
                    _online_payment.paid_amount = float(online_payment) 
                    _online_payment.reference_no = reference_no 
                    _online_payment.online_payment_type = online_payment_mode
                    _online_payment.save()
                else:
                    online_pay = OnlinePayment.objects.filter(payment=instance)
                    if online_pay.exists():
                        online_pay.delete()
                instance.description = description
                instance.save()
                return instance
        except Exception as e:
            print (traceback.format_exc(sys.exc_info()))
            raise serializers.ValidationError(e.message)        
    