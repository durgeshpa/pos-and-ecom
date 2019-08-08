from rest_framework import serializers
from payments.models import ShipmentPayment, CashPayment



class ShipmentPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentPayment
        fields = "__all__"


class CashPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashPayment
        fields = "__all__"
