from django.core.validators import RegexValidator
from rest_framework import serializers

from retailer_to_sp.models import Order, CustomerCare


class OrderNumberSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ('id', 'order_no',)


class CustomerCareSerializer(serializers.ModelSerializer):
    #order_id=OrderNumberSerializer(read_only=True)
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$')
    phone_number = serializers.CharField(validators=[phone_regex])

    class Meta:
        model=CustomerCare
        fields=('phone_number', 'complaint_id','email_us', 'order_id', 'issue_status', 'select_issue','complaint_detail')
        read_only_fields=('complaint_id','email_us','issue_status')
