import logging
from django.db import models
from django.db.models import fields
from django.http import request
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from ...models import CardData, Card, CardVersion, CardItem, Application, Page, PageCard, PageVersion, ApplicationPage

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


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
            info_logger.info(f"Create New Card Version version-{latest_version} for card  id-{card.id}, name-{card.name}")
        else:
            new_card = Card.objects.create(app=app,name=data["name"], type=data["type"])
            CardVersion.objects.create(version_number=1,
                                                            card=new_card,
                                                            card_data=new_card_data,
                                                            )
            info_logger.info(f"Created New Card with ID {new_card.id}")
        
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


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User"""

    class Meta:
        model = get_user_model()
        fields = ('id', 'first_name', 'last_name', 'phone_number', 'email', 'user_photo')

class ApplicationSerializer(serializers.ModelSerializer):
    """Application Serializer"""
    created_by = UserSerializer(required = False)

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
        data['latest_version'] = page_version.version_no
        data['created_on'] = page_version.created_on
        if page_version.published_on:
            data['published_on'] = page_version.published_on
        return data


class ApplicationDataSerializer(serializers.ModelSerializer):
    """Specific Application Serializer"""
    created_by = UserSerializer()

    class Meta:
        model = Application
        fields = ('id','name','created_on','status','created_by')

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


class PageVersionDetailSerializer(serializers.ModelSerializer):
    """Serializer for Page Version Details"""

    cards = serializers.SerializerMethodField('getPageCardMapping', required = False)

    class Meta:
        model = PageVersion
        fields = ('id', 'version_no', 'published_on', 'cards')

    def getPageCardMapping(self, obj):
        """custom serializer to get Page Card Mapping"""

        page_card = PageCard.objects.filter(page_version__id = self.instance.id).first()
        cards = PageCardSerializer(page_card)
        return cards.data


class PageSerializer(serializers.ModelSerializer):
    """Page Serializer"""

    class Meta:
        model = Page
        fields = '__all__'

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
        if self.context.get('page_version'):
            data.pop('active_version_no')
            data['version'] = PageVersionDetailSerializer(self.context.get('page_version')).data
            pass
        else:
            page = PageVersion.objects.select_related('page')
            page_versions = page.filter(page_id = instance.id)
            data['versions'] = PageVersionSerializer(page_versions, many = True).data
        apps = ApplicationPage.objects.get(page__id = instance.id).app
        data['applications'] = PageApplicationSerializer(apps).data
        return data

        