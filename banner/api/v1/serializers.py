from rest_framework import serializers
from banner.models import Banner,BannerPosition

class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class BannerSerializer(serializers.ModelSerializer):
    cat_parent = RecursiveSerializer(many=True, read_only=True)

    class Meta:
        model = Banner
        fields = ('name', 'created_at','updated_at','status', 'Type')
