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

    class Meta:
        model = ShipmentPayment
        fields = "__all__"#['description', 'cash_amount', 'payment_mode', 'reference_no', 'online_amount']  #"__all__"
        depth = 1

    def validate(self, data):
        initial_data = self.initial_data
        reference_no = initial_data['reference_no']
        if not re.match("^[a-zA-Z0-9_]*$", reference_no):
            raise serializers.ValidationError('Referece number can not have special character!')
        return initial_data  