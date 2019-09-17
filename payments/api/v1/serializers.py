import traceback
import sys
import re

from django.db import transaction
from rest_framework import serializers

from payments.models import ShipmentPayment, CashPayment, OnlinePayment, PaymentMode, \
    Payment, OrderPayment


class OrderPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderPayment
        fields = "__all__"\


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class CashPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashPayment
        fields = "__all__"


class OnlinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePayment
        fields = "__all__"
        

class ShipmentPaymentSerializer(serializers.ModelSerializer):
    parent_order_payment = OrderPaymentSerializer()

    class Meta:
        model = ShipmentPayment
        fields = ['id','parent_order_payment', 'shipment', 'paid_amount', 'description']
        #depth = 1

    # def validate(self, data):
    #     initial_data = self.initial_data
    #     reference_no = initial_data['reference_no']
    #     if not re.match("^[a-zA-Z0-9_]*$", reference_no):
    #         raise serializers.ValidationError('Referece number can not have special character!')
    #     return initial_data  

    def create(self, validated_data):
        # import pdb; pdb.set_trace()
        parent_order_payment = validated_data.pop('parent_order_payment')
        shipment = validated_data.pop('shipment')
        paid_amount = validated_data.pop('paid_amount')
        description = validated_data.pop('description')
        try:
            with transaction.atomic(): #for roll back if any exception occur
                # if payment data contains id then update else create
                parent_order_payment_inst, created = OrderPayment.objects.update_or_create(**parent_order_payment)
                parent_order_payment_inst.save()
                # create or update shipment payment instance
                shipment_payment, created = ShipmentPayment.objects.update_or_create(
                    parent_order_payment=parent_order_payment_inst,
                    shipment = shipment)
                shipment_payment.paid_amount = paid_amount
                shipment_payment.description = description
                shipment_payment.save()
                return shipment_payment
        except Exception as e:
            raise serializers.ValidationError(str(e))