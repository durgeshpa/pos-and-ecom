from django.core.validators import RegexValidator
from rest_framework import serializers

from retailer_to_sp.models import Order, CustomerCare, ReturnOrder, ReturnOrderProduct, ReturnOrderProductImage
from retailer_to_sp.api.v1.serializers import ProductSerializer, ShopSerializer

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


class ReturnOrderGFProductImageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ReturnOrderProductImage
        fields = '__all__'


class ReturnOrderGFProductSerializer(serializers.ModelSerializer):
    return_product_images = serializers.SerializerMethodField()
    
    def get_return_product_images(self, instance):
        r_product = instance.return_order.ref_return_order.return_order_products.filter(product=instance.product).last()
        return ReturnOrderGFProductImageSerializer(r_product.return_order_product_images.all(), many=True).data
    product = ProductSerializer(read_only=True)
    class Meta:
        model = ReturnOrderProduct
        fields = '__all__'


class GFReturnOrderProductSerializer(serializers.ModelSerializer):
    return_order_products = serializers.SerializerMethodField()
    seller_shop = ShopSerializer(read_only=True)
    buyer_shop = ShopSerializer(read_only=True)
    
    def get_return_order_products(self, instance):
        print(ReturnOrderProduct.objects.last().return_order.id)
        return ReturnOrderGFProductSerializer(instance.return_order_products.all(), many=True).data
    
    class Meta:
        model = ReturnOrder
        fields = ('id', 'return_no', 'shipment', 'return_type', 'return_status', 'return_order_products',
                  'return_reason', 'seller_shop', 'buyer_shop', 'created_at', 'modified_at')