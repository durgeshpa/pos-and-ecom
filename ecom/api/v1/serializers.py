from rest_framework import serializers

from django.db.models import Sum

from accounts.models import User
from addresses.models import Pincode
from categories.models import Category
from marketing.models import ReferralCode, RewardPoint, RewardLog
from shops.models import Shop
from retailer_to_sp.models import Order, OrderedProductMapping, CartProductMapping
from pos.models import RetailerProduct

from ecom.models import Address, EcomOrderAddress


class AccountSerializer(serializers.ModelSerializer):
    """
    E-Commerce User Account
    """
    name = serializers.SerializerMethodField()

    @staticmethod
    def get_name(obj):
        return obj.first_name + ' ' + obj.last_name if obj.first_name and obj.last_name else (
            obj.first_name if obj.first_name else '')

    class Meta:
        model = User
        fields = ('name', 'phone_number')


class RewardsSerializer(serializers.ModelSerializer):
    """
    Loyalty Points detail for a user
    """
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    referral_code = serializers.SerializerMethodField()
    welcome_points = serializers.SerializerMethodField()

    @staticmethod
    def get_phone(obj):
        return obj.reward_user.phone_number

    @staticmethod
    def get_email(obj):
        return obj.reward_user.email

    @staticmethod
    def get_referral_code(obj):
        return ReferralCode.user_referral_code(obj.reward_user)

    @staticmethod
    def get_welcome_points(obj):
        welcome_rwd_obj = RewardLog.objects.filter(reward_user=obj.reward_user,
                                                   transaction_type='welcome_reward').last()
        return welcome_rwd_obj.points if welcome_rwd_obj else 0

    class Meta:
        model = RewardPoint
        fields = ('phone', 'email', 'referral_code', 'redeemable_points', 'redeemable_discount', 'direct_earned',
                  'indirect_earned', 'points_used', 'welcome_points')


class UserLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name')


class AddressSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(required=False)
    state_name = serializers.CharField(required=False)

    class Meta:
        model = Address
        fields = ('id', 'user', 'type', 'address', 'contact_name', 'contact_number', 'pincode', 'city_name',
                  'state_name', 'default')
        read_only_fields = ['id', 'user']

    def validate(self, attrs):
        # Validate Pin Code
        pin_code_obj = Pincode.objects.filter(pincode=attrs.get('pincode')).select_related('city', 'city__state').last()
        if not pin_code_obj:
            raise serializers.ValidationError("Invalid Pin Code")
        # Check for address id in case of update
        pk = self.context.get('pk', None)
        user = self.context.get('user')
        if pk:
            try:
                Address.objects.get(user=user, id=pk)
                attrs['id'] = pk
            except:
                raise serializers.ValidationError("Invalid Address Id")
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        return Address.objects.create(**validated_data)

    def update(self, add_id, validated_data):
        add = Address.objects.get(id=add_id)
        add.type, add.address, add.contact_name = validated_data['type'], validated_data['address'], validated_data[
            'contact_name']
        add.contact_number, add.pincode, add.default = validated_data['contact_number'], validated_data[
            'pincode'], validated_data['default']
        add.save()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_image')


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'category_name', 'category_image')


class EcomOrderAddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = EcomOrderAddress
        fields = ('address', 'contact_name', 'contact_number', 'pincode', 'city', 'state')


class EcomOrderListSerializer(serializers.ModelSerializer):
    total_items = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    @staticmethod
    def get_total_items(obj):
        return obj.ordered_cart.aggregate(Sum('qty')).get('qty__sum')

    @staticmethod
    def get_created_at(obj):
        return obj.created_at.strftime("%b %d, %Y %-I:%M %p")

    class Meta:
        model = Order
        fields = ('id', 'order_status', 'order_amount', 'total_items', 'order_no', 'created_at')


class EcomOrderProductDetailSerializer(serializers.ModelSerializer):
    """
        Get single ordered product detail
    """
    product_name = serializers.SerializerMethodField()
    product_id = serializers.SerializerMethodField()
    product_mrp = serializers.SerializerMethodField()
    qty = serializers.SerializerMethodField()

    @staticmethod
    def get_product_id(obj):
        return obj.retailer_product.id

    @staticmethod
    def get_product_mrp(obj):
        return obj.retailer_product.mrp

    @staticmethod
    def get_product_name(obj):
        return obj.retailer_product.name

    @staticmethod
    def get_qty(obj):
        """
            qty purchased
        """
        return obj.shipped_qty

    class Meta:
        model = OrderedProductMapping
        fields = ('product_name', 'mrp', 'selling_price', 'qty')


class EcomOrderDetailSerializer(serializers.ModelSerializer):
    """
        ECom Order detail
    """
    products = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    def get_products(self, obj):
        """
            Get ordered products details
        """
        qs = OrderedProductMapping.objects.filter(ordered_product__order=obj, product_type=1)

        products = EcomOrderDetailSerializer(qs, many=True).data
        # cart offers - map free product to purchased
        product_offer_map = {}
        cart_free_product = {}
        for offer in obj.ordered_cart.offers:
            if offer['coupon_type'] == 'catalog' and offer['type'] == 'combo':
                product_offer_map[offer['item_id']] = offer
            if offer['coupon_type'] == 'cart' and offer['type'] == 'free_product':
                cart_free_product = {
                    'cart_free_product': 1,
                    'id': offer['free_item_id'],
                    'mrp': offer['free_item_mrp'],
                    'name': offer['free_item_name'],
                    'qty': offer['free_item_qty'],
                    'display_text': 'FREE on orders above ₹' + str(offer['cart_minimum_value']).rstrip('0').rstrip('.')
                }

        for product in products:
            product['display_text'] = ''
            # map purchased product with free product
            if product['product_id'] in product_offer_map:
                free_prod_info = self.get_free_product_text(product_offer_map, product)
                if free_prod_info:
                    product.update(free_prod_info)

        if cart_free_product:
            products.append(cart_free_product)
        return products

    @staticmethod
    def get_free_product_text(product_offer_map, product):
        offer = product_offer_map[product['product_id']]
        display_text = 'Free - ' + str(offer['free_item_qty_added']) + ' items of ' + str(
            offer['free_item_name']) + ' on purchase of ' + str(product['qty']) + ' items | Buy ' + str(
            offer['item_qty']) + ' Get ' + str(offer['free_item_qty'])
        return {'free_product': 1, 'display_text': display_text}

    @staticmethod
    def get_address(obj):
        address = obj.ecom_address_order
        return EcomOrderAddressSerializer(address)

    class Meta:
        model = Order
        fields = ('id', 'order_no', 'products', 'order_amount', 'address')


class EcomShipmentProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    picked_qty = serializers.IntegerField(min_value=0)
    product_type = serializers.ChoiceField(choices=[1, 0])


class EcomShipmentSerializer(serializers.ModelSerializer):
    products = EcomShipmentProductSerializer(many=True)
    order_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        shop = self.context.get('shop')
        # check if order exists
        order_id = attrs['order_id']
        order = Order.objects.filter(pk=order_id, seller_shop=shop, order_status='ordered',
                                     ordered_cart__cart_type='ECOM').last()
        if not order:
            raise serializers.ValidationError("Invalid Order Id")

        order_products = {str(i['retailer_product_id']) + "_" + str(i['product_type']): (
            i['retailer_product_id'], i['qty'], i['selling_price'], i['product_type']) for i in
            CartProductMapping.objects.filter(cart=order.ordered_cart)}

        # validate given picked products info
        products_info = attrs['products']
        given_products = []
        for item in products_info:
            key = str(item['product_id']) + "_" + str(item['product_type'])
            if key not in order_products:
                raise serializers.ValidationError("{} Invalid product info")
            if item['picked_qty'] > order_products[item['product_id']][1]:
                raise serializers.ValidationError("Picked quantity should be less than ordered quantity")

            given_products += [key]
            item['selling_price'] = order_products[item['product_id']][2]

        for prod in order_products:
            if prod not in given_products:
                products_info.append({
                    "product_id": int(order_products[prod][0]),
                    "picked_qty": 0,
                    "product_type": int(order_products[prod][3]),
                    "selling_price": int(order_products[prod][2])
                })

        attrs['products'] = products_info
        return attrs
