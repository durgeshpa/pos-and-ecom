from rest_framework import serializers
from banner.models import Banner, BannerPosition, BannerData, BannerSlot, HomePageMessage
from brand.models import Brand


class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', "brand_name")


class BannerSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)

    class Meta:
        model = Banner
        fields = ('name', 'image', 'banner_type', 'category', 'brand', 'products', 'status', 'banner_start_date',
                  'banner_end_date', 'alt_text', 'text_below_image')


class BannerPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannerPosition
        fields = '__all__'


class BannerDataSerializer(serializers.ModelSerializer):
    banner_data = BannerSerializer(read_only=True)
    slot = BannerPositionSerializer(read_only=True)

    class Meta:
        model = BannerData
        fields = ('id', 'slot', 'banner_data', 'banner_data_order')


class BannerSlotSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = BannerPosition
        fields = '__all__'


class HomePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomePageMessage
        fields = '__all__'
