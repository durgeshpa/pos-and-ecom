import traceback
import sys

from django.db import transaction
from rest_framework import serializers

from payments.models import ShipmentPayment, CashPayment, OnlinePayment


class CashPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashPayment
        fields = "__all__"


class OnlinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePayment
        fields = "__all__"
        

class ShipmentPaymentSerializer(serializers.ModelSerializer):
    cash_amount = serializers.CharField(write_only=True)
    payment_mode = serializers.CharField(write_only=True)
    reference_no = serializers.CharField(write_only=True)
    online_amount = serializers.CharField(write_only=True)

    #cash_payment = CashPaymentSerializer(fields=['paid_amount'])
    #online_payment = OnlinePaymentSerializer()
    class Meta:
        model = ShipmentPayment
        fields = ['cash_amount', 'payment_mode', 'reference_no', 'online_amount']  #"__all__"

    def update(self, instance, validated_data):
        
        try:
            with transaction.atomic():
                #import pdb; pdb.set_trace()
                cash_payment = validated_data.pop('cash_amount')
                _cash_payment = CashPayment.objects.get(payment=instance)
                _cash_payment.paid_amount = float(cash_payment) #.paid_amount
                _cash_payment.save()

                # online_payment_mode = validated_data.pop('payment_mode')
                # if online_payment_mode:
                #     reference_no = validated_data.pop('reference_no')
                #     online_payment = validated_data.pop('online_amount')
                #     _online_payment, created = OnlinePayment.objects.get_or_create(payment=instance)
                #     _online_payment.paid_amount = float(online_payment) 
                #     _online_payment.reference_no = reference_no
                #     _online_payment.save()

                return instance
        except Exception as e:
            print (traceback.format_exc(sys.exc_info()))
            raise serializers.ValidationError(e.message)        
    