from django import forms
from gram_to_brand.models import Order,GRNOrder

# from gram_to_brand.models import OrderShipment,CarOrderShipmentMapping
#
# class OrderShipmentFrom(forms.ModelForm):
#     #cart_product_ship = forms.ModelChoiceField(queryset=CartProductMapping.objects.all())
#     #car_order_shipment_mapping = forms.ModelChoiceField(queryset=CarOrderShipmentMapping.objects.all())
#     delivered_qty = forms.IntegerField()
#     changed_price = forms.FloatField(min_value=0)
#     manufacture_date = forms.DateField()
#     expiry_date = forms.DateField()
#
#     class Meta:
#         model = OrderShipment
#         fields = ('delivered_qty','changed_price','manufacture_date','expiry_date',)
#
#     def __init__(self):
#         print("fgfdgfd")
#
# from django import forms
# from .models import Order
#
#
# class OrderMappingForm(forms.ModelForm):
#
#     # here we only need to define the field we want to be editable
#     ordered_shipment = forms.ModelMultipleChoiceField(queryset=CarOrderShipmentMapping.objects.all(), required=False)


# class OrderSearch(forms.ModelForm):
#     def clean_order_no(self):
#         order_no = self.cleaned_data.get('order',None)
#         print(order_no)
#
#     class Meta:
#         model = GRNOrder
#         fields = ('order','order_item',)
#
#     def __init__(self, *args, **kwargs):
#         super(OrderSearch, self).__init__(*args, **kwargs)
#         #choices = [self.fields['order'].choices.__iter__().next()]
#         print(self.fields['order'])


# class OrderSearch(forms.ModelForm):
#   order = forms.ModelChoiceField(queryset=Order.objects.all(),label=u"order",required=False)
#
#   class Meta:
#     fields = '__all__'
#     model = GRNOrderclass ItemForm(ModelForm):


# class GRNOrderProductMappingForm(ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(GRNOrderProductMappingForm, self).__init__(*args, **kwargs)
#         instance = getattr(self, 'instance', None)
#         if instance and instance.pk:
#             self.fields['already_grned_product'].widget.attrs['readonly'] = True
#
#     def clean_sku(self):
#         instance = getattr(self, 'instance', None)
#         if instance and instance.pk:
#             return instance.already_grned_product
#         else:
#             return self.cleaned_data['already_grned_product']
