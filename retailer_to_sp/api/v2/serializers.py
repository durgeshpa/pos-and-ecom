from django.core.validators import RegexValidator
from rest_framework import serializers

from retailer_to_sp.models import Order, CustomerCare, ReturnOrder, ReturnOrderProduct, ReturnOrderProductImage
from retailer_to_sp.api.v1.serializers import ProductSerializer, ShopRouteBasicSerializers
from addresses.models import ShopRoute
from shops.models import Shop
from accounts.api.v1.serializers import PosShopUserSerializer

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


class ShopSerializer(serializers.ModelSerializer):
    owner_number = serializers.SerializerMethodField()
    def get_owner_number(self, instance):
        return instance.shop_owner.phone_number 
    
    class Meta:
        model = Shop
        fields = ('id', 'shop_name', 'owner_number')


class GFReturnOrderProductSerializer(serializers.ModelSerializer):
    return_order_products = serializers.SerializerMethodField()
    seller_shop = ShopSerializer(read_only=True)
    buyer_shop = ShopSerializer(read_only=True)
    buyer = serializers.SerializerMethodField()
    
    def get_return_order_products(self, instance):
        return ReturnOrderGFProductSerializer(instance.return_order_products.all(), many=True).data
    
    def get_buyer(self, instance):
        buyer = instance.ref_return_order.buyer
        return PosShopUserSerializer(buyer).data
                
    class Meta:
        model = ReturnOrder
        fields = ('id', 'return_no', 'shipment', 'return_type', 'return_status', 'return_order_products',
                  'return_reason', 'seller_shop', 'buyer_shop', 'created_at', 'modified_at')



class ReturnChallanSerializer(serializers.ModelSerializer):

    no_of_challan = serializers.IntegerField()
    warehouse=serializers.SerializerMethodField()
    buyer_shop__shop_routes = serializers.SerializerMethodField()

    def get_buyer_shop__shop_routes(self,obj):
        shop_route = ShopRoute.objects.get(id=obj["buyer_shop__shop_routes"])
        return ShopRouteBasicSerializers(shop_route, read_only=True).data

    def get_warehouse(self,obj):
        shop = Shop.objects.get(id=obj["warehouse"])
        return ShopSerializer(shop,read_only=True).data

    class Meta:
        model = ReturnOrder
        fields = ('buyer_shop__shop_routes', 'no_of_challan', 'warehouse')
