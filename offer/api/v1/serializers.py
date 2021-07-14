from rest_framework import serializers
from offer.models import OfferBanner, OfferBannerPosition, OfferBannerData, OfferBannerSlot, TopSKU, OfferPage
from brand.models import Brand


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
            'status',
            'offer_banner_start_date', 'offer_banner_end_date', 'alt_text', 'text_below_image')

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


class OfferPageSerializers(serializers.ModelSerializer):
    class Meta:
        model = OfferPage
        fields = ('id', 'name',)


class OfferBannerSlotSerializers(serializers.ModelSerializer):
    class Meta:
        model = OfferPage
        fields = ('id', 'name', 'page')
