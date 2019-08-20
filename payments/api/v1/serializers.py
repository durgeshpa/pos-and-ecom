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
    #cash_payment = CashPaymentSerializer(fields=['paid_amount'])
    #online_payment = OnlinePaymentSerializer()
    class Meta:
        model = ShipmentPayment
        fields = ['cash_amount']  #"__all__"

    def update(self, instance, validated_data):
        
        try:
            with transaction.atomic():
                #import pdb; pdb.set_trace()
                cash_payment = validated_data.pop('cash_amount')
                _cash_payment = CashPayment.objects.get(payment=instance)
                _cash_payment.paid_amount = float(cash_payment) #.paid_amount
                _cash_payment.save()

                return instance
        except Exception as e:
            print (traceback.format_exc(sys.exc_info()))
            raise serializers.ValidationError(e.message)        

    