from rest_framework import serializers
from django.shortcuts import get_object_or_404

from ...models import CardData, Card, CardVersion, CardItem, Application, Page, PageVersion


class CardAppSerializer(serializers.ModelSerializer):
    """Serializer for Application"""

    class Meta:
        model = Application
        fields = ("id", "name", "status",)


class CardItemSerializer(serializers.ModelSerializer):
    """Serializer for CardItem"""

    class Meta:
        model = CardItem
        # fields = "__all__"
        exclude = ('card_data',)


class CardDataSerializer(serializers.ModelSerializer):
    """Serializer for CardData"""

    items = CardItemSerializer(many=True)
    class Meta:
        model = CardData
        fields = '__all__'
    
    def create(self, validated_data):
        request = self.context.get("request")
        data = request.data
        app_id = data.get("app_id")
        items = validated_data.pop("items")
        new_card_data = CardData.objects.create(**validated_data)
        for item in items:
            CardItem.objects.create(card_data=new_card_data,**item)
        app = get_object_or_404(Application, id=app_id)
        card = Card.objects.filter(name=data.get("name")).first()
        if card:
            latest_version = card.versions.all().order_by('-version_number').first().version_number + 1
            CardVersion.objects.create(version_number=latest_version,
                                                            card=card,
                                                            card_data=new_card_data,
                                                            )
        else:
            new_card = Card.objects.create(app=app,name=data["name"], type=data["type"])
            CardVersion.objects.create(version_number=1,
                                                            card=new_card,
                                                            card_data=new_card_data,
                                                            )
        return new_card_data

class CardSerializer(serializers.ModelSerializer):
    """Serializer for Card"""

    app = CardAppSerializer()
    card_data = serializers.SerializerMethodField("getCardData", required=False)

    def getCardData(self, card):
        """custom serializer method to get cardData"""

        latest_version = card.versions.all().order_by('-version_number').first()
        card_data = latest_version.card_data
        card_data = CardDataSerializer(card_data)
        return card_data.data

    class Meta:
        model = Card
        depth = 1
        fields = '__all__'


class ApplicationSerializer(serializers.ModelSerializer):
    """Application Serializer"""

    class Meta:
        model = Application
        fields = '__all__'


class ApplicationPageSerializer(serializers.ModelSerializer):
    """Page Serializer"""

    class Meta:
        model = Page
        fields = '__all__'

    def to_representation(self, instance):
        """ Adding Page Version Details """
        data = super().to_representation(instance)
        page_version = PageVersion.objects.filter(page=instance.id).order_by('-version_no').first()
        data['version'] = page_version.version_no
        data['created_on'] = page_version.created_on
        if page_version.published_on:
            data['published_on'] = page_version.published_on
        return data


class ApplicationDataSerializer(serializers.ModelSerializer):
    """Specific Application Serializer"""

    class Meta:
        model = Application
        fields = '__all__'

    def to_representation(self, instance):
        """ Page Version Details"""
        data = super().to_representation(instance)
        # Page Details of an Application
        pages = Page.objects.filter(app_pages__app=instance.id)
        data['pages'] = ApplicationPageSerializer(pages, many=True).data
        return data
