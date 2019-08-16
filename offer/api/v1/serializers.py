from rest_framework import serializers
from offer.models import OfferBanner,OfferBannerPosition,OfferBannerData,OfferBannerSlot,TopSKU
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
    brand = BrandSerializer(read_only=True)

    class Meta:
        model = OfferBanner
        fields = ('name','image','offer_banner_type','category','brand','products','status','offer_banner_start_date','offer_banner_end_date','alt_text','text_below_image')

class OfferBannerPositionSerializer(serializers.ModelSerializer):

    class Meta:
        model = OfferBannerPosition
        fields = '__all__'


class OfferBannerDataSerializer(serializers.ModelSerializer):
    offer_banner_data = OfferBannerSerializer(read_only=True)
    slot = OfferBannerPositionSerializer(read_only=True)
    class Meta:
        model = OfferBannerData
        fields = ('id','slot','offer_banner_data','offer_banner_data_order')

class OfferBannerSlotSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = OfferBannerPosition
        fields = '__all__'

class TopSKUSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopSKU
        fields = ('product',)
