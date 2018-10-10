from rest_framework import serializers
from banner.models import Banner,BannerPosition,BannerData,BannerSlot

class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class BannerSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = Banner
        fields = '__all__'

class BannerPositionSerializer(serializers.ModelSerializer):

    class Meta:
        model = BannerPosition
        fields = '__all__'


class BannerDataSerializer(serializers.ModelSerializer):
    banner_data = BannerSerializer(read_only=True)
    slot = BannerPositionSerializer(read_only=True)
    class Meta:
        model = BannerData
        fields = ('id','slot','banner_data','banner_data_order')

class BannerSlotSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = BannerPosition
        fields = '__all__'
