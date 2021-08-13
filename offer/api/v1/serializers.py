from django.db import transaction

from rest_framework import serializers
from offer.models import OfferBanner, OfferBannerPosition, OfferBannerData, OfferBannerSlot, TopSKU, OfferPage
from brand.models import Brand
from offer.models import OfferLog
from offer.common_function import OfferCls
from offer.common_validators import get_validate_page
from products.api.v1.serializers import UserSerializers, ProductSerializers
from shops.api.v2.serializers import ServicePartnerShopsSerializer
from products.common_validators import get_validate_product, get_validate_seller_shop


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
        fields = (
            'name', 'image', 'offer_banner_type', 'category', 'sub_category', 'brand', 'sub_brand', 'products',
            'status', 'offer_banner_start_date', 'offer_banner_end_date', )

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
    class Meta:
        model = TopSKU
        fields = ('product',)


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
            if OfferPage.objects.filter(name__iexact=self.initial_data['name'], status=True).exclude(id=offer_page_id).exists():
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


class OfferBannerSlotSerializers(serializers.ModelSerializer):
    page = OfferPageListSerializers(read_only=True)
    offer_banner_slot_log = OfferLogSerializers(many=True, read_only=True)

    class Meta:
        model = OfferBannerSlot
        fields = ('id', 'name', 'page', 'offer_banner_slot_log')

    def validate(self, data):
        offer_page_id = self.instance.id if self.instance else None
        if 'name' in self.initial_data and self.initial_data['name']:
            if OfferPage.objects.filter(name__iexact=self.initial_data['name'], status=True).exclude(id=offer_page_id).exists():
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
    product = ProductSerializers(read_only=True)
    top_sku_log = OfferLogSerializers(many=True, read_only=True)
    start_date = serializers.DateTimeField(required=True)
    end_date = serializers.DateTimeField(required=True)

    class Meta:
        model = TopSKU
        fields = ('id', 'shop', 'product', 'start_date', 'end_date', 'top_sku_log', 'status')

    def validate(self, data):
        if self.initial_data['product'] is None:
            raise serializers.ValidationError("please select product")
        product_val = get_validate_product(self.initial_data['product'])
        if 'error' in product_val:
            raise serializers.ValidationError(product_val['error'])
        data['product'] = product_val['product']

        if self.initial_data['shop']:
            seller_shop_val = get_validate_seller_shop(self.initial_data['shop'])
            if 'error' in seller_shop_val:
                raise serializers.ValidationError(seller_shop_val['error'])
            data['shop'] = seller_shop_val['seller_shop']

        if self.initial_data['end_date'] <= self.initial_data['start_date']:
            raise serializers.ValidationError("End date should be greater than start date.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new TopSKU """
        try:
            off_page = TopSKU.objects.create(**validated_data)
            OfferCls.create_top_sku_log(off_page, "created")
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return off_page

    @transaction.atomic
    def update(self, instance, validated_data):
        """update TopSKU"""
        try:
            instance = super().update(instance, validated_data)
            OfferCls.create_top_sku_log(instance, "updated")
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
