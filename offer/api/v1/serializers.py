from datetime import datetime

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from offer.models import OfferBanner, OfferBannerPosition, OfferBannerData, OfferBannerSlot, TopSKU, OfferPage, TopSKUProduct
from brand.models import Brand
from offer.models import OfferLog
from offer.common_function import OfferCls
from products.models import Product
from offer.common_validators import get_validate_page, get_validate_offerbannerslot, get_validated_offer_ban_data, \
    get_validate_products
from products.api.v1.serializers import UserSerializers, BrandSerializers, CategorySerializers, ProductSerializers
from shops.api.v2.serializers import ServicePartnerShopsSerializer
from products.common_validators import get_validate_product, get_validate_seller_shop, get_validate_parent_brand
from categories.common_validators import get_validate_category


class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', "brand_name")


class OfferBannerSerializer(serializers.ModelSerializer):
    brand = serializers.SerializerMethodField('product_brand')
    category = serializers.SerializerMethodField('product_category')
    sub_brand = serializers.SerializerMethodField('product_sub_brand')
    sub_category = serializers.SerializerMethodField('product_sub_category')

    class Meta:
        model = OfferBanner
        fields = ('name', 'image', 'offer_banner_type', 'category', 'sub_category', 'brand', 'sub_brand', 'products',
                  'status', 'offer_banner_start_date', 'offer_banner_end_date',)

    def product_category(self, obj):
        if obj.category_id is None:
            return obj.sub_category_id
        return obj.category_id

    def product_brand(self, obj):
        try:
            if obj.brand_id is None:
                # return None
                return {"id": obj.sub_brand_id, "brand_name": obj.sub_brand.brand_name}
            return {"id": obj.brand_id, "brand_name": obj.brand.brand_name}
        except:
            return None

    def product_sub_category(self, obj):
        if obj.sub_category_id is None:
            return None
        return obj.sub_category_id

    def product_sub_brand(self, obj):
        try:
            if obj.sub_brand_id is None:
                return None
            return {"id": obj.sub_brand_id, "brand_name": obj.sub_brand.brand_name}
        except:
            return None


class OfferBannerPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferBannerPosition
        fields = '__all__'


class OfferBannerDataSerializer(serializers.ModelSerializer):
    offer_banner_data = OfferBannerSerializer(read_only=True)
    slot = OfferBannerPositionSerializer(read_only=True)

    class Meta:
        model = OfferBannerData
        fields = ('id', 'slot', 'offer_banner_data', 'offer_banner_data_order')


class OfferBannerSlotSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = OfferBannerPosition
        fields = '__all__'


class TopSKUSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    def get_products(self, obj):
        top_sku = obj.offer_top_sku.all().values('product__id')
        products = Product.objects.filter(id__in = top_sku)
        data = ProductSerializers(products, many=True).data
        return data

    class Meta:
        model = TopSKU
        fields = ('products',)

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)


class OfferLogSerializers(serializers.ModelSerializer):
    updated_by = UserSerializers(read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['update_at'] = instance.update_at.strftime("%b %d %Y %I:%M%p")
        return representation

    class Meta:
        model = OfferLog
        fields = ('update_at', 'updated_by')


class OfferPageSerializers(serializers.ModelSerializer):
    offer_page_log = OfferLogSerializers(many=True, read_only=True)

    class Meta:
        model = OfferPage
        fields = ('id', 'name', 'offer_page_log')

    def validate(self, data):
        offer_page_id = self.instance.id if self.instance else None
        if 'name' in self.initial_data and self.initial_data['name']:
            if OfferPage.objects.filter(name__iexact=self.initial_data['name'], status=True).exclude(
                    id=offer_page_id).exists():
                raise serializers.ValidationError(f"offer page with name {self.initial_data['name']} already exists.")
        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new offer page"""
        try:
            off_page = OfferPage.objects.create(**validated_data)
            OfferCls.create_offer_page_log(off_page, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return off_page

    @transaction.atomic
    def update(self, instance, validated_data):
        """update Offer Page"""
        try:
            instance = super().update(instance, validated_data)
            OfferCls.create_offer_page_log(instance, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['name']:
            representation['name'] = representation['name'].title()
        return representation


class OfferPageListSerializers(serializers.ModelSerializer):
    class Meta:
        model = OfferPage
        fields = ('id', 'name',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['name']:
            representation['name'] = representation['name'].title()
        return representation


class OfferBannerSlotSerializers(serializers.ModelSerializer):
    page = OfferPageListSerializers(read_only=True)
    offer_banner_slot_log = OfferLogSerializers(many=True, read_only=True)

    class Meta:
        model = OfferBannerSlot
        fields = ('id', 'name', 'page', 'offer_banner_slot_log')

    def validate(self, data):
        offer_banner_slot_id = self.instance.id if self.instance else None
        if 'name' in self.initial_data and self.initial_data['name']:
            if OfferBannerSlot.objects.filter(name__iexact=self.initial_data['name'], status=True).exclude(
                    id=offer_banner_slot_id).exists():
                raise serializers.ValidationError(f"offer banner slot with name {self.initial_data['name']} "
                                                  f"already exists.")

        if not 'page' in self.initial_data or not self.initial_data['page']:
            raise serializers.ValidationError('page is required')

        page_val = get_validate_page(self.initial_data['page'])
        if 'error' in page_val:
            raise serializers.ValidationError(f'{page_val["error"]}')
        data['page'] = page_val['page']

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new offer banner slot"""
        try:
            offer_banner_slot = OfferBannerSlot.objects.create(**validated_data)
            OfferCls.create_offer_banner_slot_log(offer_banner_slot, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return offer_banner_slot

    @transaction.atomic
    def update(self, instance, validated_data):
        """update Offer Banner Slot"""
        try:
            instance = super().update(instance, validated_data)
            OfferCls.create_offer_banner_slot_log(instance, "updated")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['name']:
            representation['name'] = representation['name'].title()
        return representation


class TopSKUSerializers(serializers.ModelSerializer):
    shop = ServicePartnerShopsSerializer(read_only=True)
    top_sku_log = OfferLogSerializers(many=True, read_only=True)
    products = serializers.SerializerMethodField()
    start_date = serializers.DateTimeField(required=True)
    end_date = serializers.DateTimeField(required=True)

    class Meta:
        model = TopSKU
        fields = ('id', 'shop', 'products', 'start_date', 'end_date', 'top_sku_log', 'status')

    def get_products(self, obj):
        top_sku = obj.offer_top_sku.all().values('product__id')
        products = Product.objects.filter(id__in = top_sku)
        data = ProductSerializers(products, many=True).data
        return data

    

    def validate(self, data):

        if 'shop' in self.initial_data and self.initial_data['shop']:
            seller_shop_val = get_validate_seller_shop(self.initial_data['shop'])
            if 'error' in seller_shop_val:
                raise serializers.ValidationError(seller_shop_val['error'])
            data['shop'] = seller_shop_val['seller_shop']

        if self.initial_data['end_date'] <= self.initial_data['start_date']:
            raise serializers.ValidationError("End date should be greater than start date.")

        return data

    def validate_product(self,obj):
        if len(obj) == 0:
            raise serializers.ValidationError("please select product")
        data = []
        for product in obj:
            product_val = get_validate_product(product)
            if 'error' in product_val:
                raise serializers.ValidationError(product_val['error'])
            data.append(product_val['product'])
        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new TopSKU """
        products = self.context.get('products')
        validated_product = self.validate_product(products)
        try:
            off_page = TopSKU.objects.create(**validated_data)
            for product in validated_product:
                TopSKUProduct.objects.create(top_sku = off_page, product = product)
            OfferCls.create_top_sku_log(off_page, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return off_page

    @transaction.atomic
    def update(self, instance, validated_data):
        """update TopSKU"""
        products = self.context.get('products')
        if products is not None:
            validated_product = self.validate_product(products)
        try:
            instance = super().update(instance, validated_data)
            OfferCls.create_top_sku_log(instance, "updated")
            if products is not None:
                TopSKUProduct.objects.filter(top_sku=instance).delete()
                for product in validated_product:
                    TopSKUProduct.objects.create(top_sku = instance, product = product)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return instance

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     if instance.start_date:
    #         representation['start_date'] = instance.start_date.strftime("%b %d %Y %I:%M%p")
    #     if instance.end_date:
    #         representation['end_date'] = instance.end_date.strftime("%b %d %Y %I:%M%p")
    #     return representation


class OfferBannerListSlotSerializers(serializers.ModelSerializer):
    # page = OfferPageListSerializers(read_only=True)

    class Meta:
        model = OfferBannerSlot
        fields = ('id', '__str__',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return {
            "id": representation['id'],
            "offerbannerslot": representation['__str__']
        }


class OfferBannerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferBanner
        fields = ('id', 'name', '__str__')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return {
            "id": representation['id'],
            "name": representation['name'].title(),
            "value": representation['__str__']
        }


class OfferBannerDataListSerializer(serializers.ModelSerializer):
    offer_banner_data = OfferBannerListSerializer()

    class Meta:
        model = OfferBannerData
        fields = ('__str__', 'offer_banner_data')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return {
            "offerbannerdata": representation['__str__'],
            "offer_banner_data": representation['offer_banner_data']
        }


class OfferBannerPositionSerializers(serializers.ModelSerializer):
    page = OfferPageListSerializers(read_only=True)
    shop = ServicePartnerShopsSerializer(read_only=True)
    offerbannerslot = OfferBannerListSlotSerializers(read_only=True)
    offer_ban_data = OfferBannerDataListSerializer(many=True, read_only=True)

    class Meta:
        model = OfferBannerPosition
        fields = ('id', 'shop', 'page', 'offer_banner_position_order', 'offerbannerslot', 'offer_ban_data',
                  '__str__')

    def validate(self, data):
        if self.initial_data['shop']:
            seller_shop_val = get_validate_seller_shop(self.initial_data['shop'])
            if 'error' in seller_shop_val:
                raise serializers.ValidationError(seller_shop_val['error'])
            data['shop'] = seller_shop_val['seller_shop']

        if 'page' not in self.initial_data or not self.initial_data['page']:
            raise serializers.ValidationError('page is required')

        page_val = get_validate_page(self.initial_data['page'])
        if 'error' in page_val:
            raise serializers.ValidationError(f'{page_val["error"]}')
        data['page'] = page_val['page']

        if 'offerbannerslot' not in self.initial_data or not self.initial_data['offerbannerslot']:
            raise serializers.ValidationError('offerbannerslot is required')

        offerbannerslot_val = get_validate_offerbannerslot(self.initial_data['offerbannerslot'])
        if 'error' in offerbannerslot_val:
            raise serializers.ValidationError(f'{offerbannerslot_val["error"]}')
        data['offerbannerslot'] = offerbannerslot_val['off_banner_slot']

        if 'offer_ban_data' in self.initial_data and self.initial_data['offer_ban_data']:
            validated_offer_ban_data = get_validated_offer_ban_data(self.initial_data['offer_ban_data'])
            if 'error' in validated_offer_ban_data:
                raise serializers.ValidationError(f'{validated_offer_ban_data["error"]}')

            data['offer_ban_data'] = self.initial_data['offer_ban_data']

        return data

    @transaction.atomic
    def create(self, validated_data):
        offer_ban_data = validated_data.pop('offer_ban_data', None)
        """create a new offer banner position """
        try:
            offer_banner_slot = OfferBannerPosition.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if offer_ban_data:
            self.create_offer_banner_data(offer_banner_slot, offer_ban_data)

        return offer_banner_slot

    @transaction.atomic
    def update(self, instance, validated_data):
        offer_ban_data = validated_data.pop('offer_ban_data', None)
        """update offer banner position"""
        try:
            instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if offer_ban_data:
            self.create_offer_banner_data(instance, offer_ban_data)

        return instance

    # crete offer banner
    def create_offer_banner_data(self, offer_banner_slot, offer_ban_data):
        offer_slot = OfferBannerData.objects.filter(slot=offer_banner_slot)
        if offer_slot.exists():
            offer_slot.delete()

        for data in offer_ban_data:
            OfferBannerData.objects.create(slot=offer_banner_slot,
                                           offer_banner_data_id=data['offer_banner_data'])

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        obj = representation.copy()
        obj.pop('__str__')
        obj['offer_banner_position'] = representation['__str__']
        return obj


class OfferBannerSerializers(serializers.ModelSerializer):
    sub_category = CategorySerializers(read_only=True)
    brand = BrandSerializers(read_only=True)
    category = CategorySerializers(read_only=True)
    sub_brand = BrandSerializers(read_only=True)
    products = ProductSerializers(many=True, read_only=True)
    offer_banner_log = OfferLogSerializers(many=True, read_only=True)

    class Meta:
        model = OfferBanner
        fields = ('id', 'name', 'image', 'offer_banner_type', 'category', 'sub_category', 'brand', 'sub_brand',
                  'products', 'status', 'offer_banner_start_date', 'created_at', 'offer_banner_end_date',
                  'offer_banner_log')

    def validate(self, data):
        """
            data validation.
        """

        if 'brand' in self.initial_data and self.initial_data['brand']:
            parent_brand_val = get_validate_parent_brand(self.initial_data['brand'])
            if 'error' in parent_brand_val:
                raise serializers.ValidationError(parent_brand_val['error'])
            data['brand'] = parent_brand_val['parent_brand']

        if 'sub_brand' in self.initial_data and self.initial_data['sub_brand']:
            sub_brand_brand_val = get_validate_parent_brand(self.initial_data['sub_brand'])
            if 'error' in sub_brand_brand_val:
                raise serializers.ValidationError(sub_brand_brand_val['error'])
            data['sub_brand'] = sub_brand_brand_val['parent_brand']

        if 'category' in self.initial_data and self.initial_data['category']:
            category_val = get_validate_category(self.initial_data['category'])
            if 'error' in category_val:
                raise serializers.ValidationError(_(category_val["error"]))
            data['category'] = category_val['category']

        if 'sub_category' in self.initial_data and self.initial_data['sub_category']:
            sub_category_val = get_validate_category(self.initial_data['sub_category'])
            if 'error' in sub_category_val:
                raise serializers.ValidationError(_(sub_category_val["error"]))
            data['sub_category'] = sub_category_val['category']

        if 'products' in self.initial_data and self.initial_data['products']:
            products_val = get_validate_products(self.initial_data['products'])
            if 'error' in products_val:
                raise serializers.ValidationError(_(products_val["error"]))
            data['products'] = products_val["products"]

        if self.initial_data['offer_banner_type'] == 'brand' and self.initial_data['brand'] is None:
            raise serializers.ValidationError('Please select the Brand')
        if self.initial_data['offer_banner_type'] == 'category' and self.initial_data['category'] is None:
            raise serializers.ValidationError('Please select the Category')
        if self.initial_data['offer_banner_type'] == 'subbrand' and self.initial_data['sub_brand'] is None:
            raise serializers.ValidationError('Please select the SubBrand')
        if self.initial_data['offer_banner_type'] == 'subcategory' and self.initial_data['sub_category'] is None:
            raise serializers.ValidationError('Please select the SubCategory')
        if self.initial_data['offer_banner_type'] == 'product' and (
                self.initial_data['products'] is None or len(self.initial_data['products']) == 0):
            raise serializers.ValidationError('Please select at least one Product')

        if 'offer_banner_start_date' in self.initial_data and self.initial_data['offer_banner_start_date'] and \
                datetime.strptime(self.initial_data['offer_banner_start_date'],
                                  '%Y-%m-%dT%H:%M:%S').date() < datetime.today().date():
            raise serializers.ValidationError("offer banner start date should be greater than today.")

        if 'offer_banner_start_date' in self.initial_data and 'offer_banner_end_date' in self.initial_data and \
                self.initial_data['offer_banner_start_date'] and self.initial_data['offer_banner_end_date']:
            if datetime.strptime(self.initial_data['offer_banner_start_date'], '%Y-%m-%dT%H:%M:%S').date() >= \
                    datetime.strptime(self.initial_data['offer_banner_end_date'], '%Y-%m-%dT%H:%M:%S').date():
                raise serializers.ValidationError("banner end date should be greater than"
                                                  " banner start date.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        products = validated_data.pop('products', None)
        try:
            offer_banner = OfferBanner.objects.create(**validated_data)
            if products:
                for pro in products:
                    offer_banner.products.add(pro)

            OfferCls.create_offer_banner_log(offer_banner, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return offer_banner

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            offer_banner = super().update(instance, validated_data)
            OfferCls.create_offer_banner_log(offer_banner, "updated")

        except Exception as e:
            error = {'message': e.args[0] if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return offer_banner

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['name']:
            representation['name'] = representation['name'].title()
        return representation
