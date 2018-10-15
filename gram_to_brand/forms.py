from django import forms
from gram_to_brand.models import OrderShipment,CarOrderShipmentMapping

class OrderShipmentFrom(forms.ModelForm):
    #cart_product_ship = forms.ModelChoiceField(queryset=CartProductMapping.objects.all())
    #car_order_shipment_mapping = forms.ModelChoiceField(queryset=CarOrderShipmentMapping.objects.all())
    delivered_qty = forms.IntegerField()
    changed_price = forms.FloatField(min_value=0)
    manufacture_date = forms.DateField()
    expiry_date = forms.DateField()

    class Meta:
        model = OrderShipment
        fields = ('delivered_qty','changed_price','manufacture_date','expiry_date',)

    def __init__(self):
        print("fgfdgfd")

from django import forms
from .models import Order


class OrderMappingForm(forms.ModelForm):

    # here we only need to define the field we want to be editable
    ordered_shipment = forms.ModelMultipleChoiceField(queryset=CarOrderShipmentMapping.objects.all(), required=False)