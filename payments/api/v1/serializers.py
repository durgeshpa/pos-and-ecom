from rest_framework import serializers
from payments.models import ShipmentPayment, CashPayment, OnlinePaymentSerializer



class ShipmentPaymentSerializer(serializers.ModelSerializer):
    cash_payment = CashPaymentSerializer()
    online_payment = OnlinePaymentSerializer()
    class Meta:
        model = ShipmentPayment
        fields = "__all__"


class CashPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashPayment
        fields = "__all__"


class OnlinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePayment
        fields = "__all__"
        