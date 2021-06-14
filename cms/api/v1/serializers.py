from django.db import models
from django.db.models import fields
from django.http import request
from rest_framework import serializers
from django.shortcuts import get_object_or_404

from ...models import CardData, Card, CardVersion, CardItem, Application, Page, PageCard, PageVersion, ApplicationPage


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
        read_only_fields = ['created_by']

        
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


class PageVersionSerializer(serializers.ModelSerializer):
    """Serializer for Page Version"""

    class Meta:
        model = PageVersion
        fields = ('id', 'version_no', 'published_on',)


class PageApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application of the Page"""

    class Meta:
        model = Application
        fields = ('id', 'name',) 


class PageCardSerializer(serializers.ModelSerializer):
    """ Serializer for Page Card Mapping"""
    
    class Meta:
        model = PageCard
        fields = ('card_version', 'card_pos', 'card_priority')


class PageSerializer(serializers.ModelSerializer):
    """Page Serializer"""

    class Meta:
        model = Page
        fields = '__all__'
        depth = 1

    def to_representation(self, instance):
        data = super().to_representation(instance)
        page_version = PageVersion.objects.filter(page = instance.id)
        data['version'] = PageVersionSerializer(page_version, many = True).data
        app = ApplicationPage.objects.select_related('app').get(page = instance.id).app
        data['application'] = PageApplicationSerializer(app).data
        return data

    def create(self, validated_data):
        data = self.context.get("request").data
        app_id = data.get("app_id")
        cards = data.get("cards")
        # Create new Page
        new_page = Page.objects.create(**validated_data)
        # Mapping Page and Application
        app = get_object_or_404(Application, id = app_id)
        ApplicationPage.objects.create(app = app, page = new_page)
        # Creating Page Version
        new_page_version = PageVersion.objects.create(page = new_page, version_no = 1)
        # Mapping Cards of Pages
        for card in cards:
            PageCard.objects.create(page_version = new_page_version, **card)
        return new_page
        

class PageDetailSerializer(serializers.ModelSerializer):
    """Serializer for Specific Page"""

    class Meta:
        model = Page
        fields = '__all__'

    def to_representation(self, instance):
        data =  super().to_representation(instance)
        page = PageVersion.objects.select_related('page')
        page_versions = page.filter(page_id = instance.id)
        data['versions'] = PageVersionSerializer(page_versions, many = True).data
        return data

        