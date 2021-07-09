import logging
from datetime import datetime
from django.utils.six import indexbytes
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound, ValidationError

from ...models import CardData, Card, CardVersion, CardItem, Application, Page, PageCard, PageVersion, ApplicationPage
from cms.messages import VALIDATION_ERROR_MESSAGES, SUCCESS_MESSAGES, ERROR_MESSAGES


info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.

    Updated for Django REST framework 3.
    """

    def to_internal_value(self, data):
        from django.core.files.base import ContentFile
        import base64
        import six
        import uuid

        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            # Check if the base64 string is in the "data:" format
            if 'data:' in data and ';base64,' in data:
                # Break out the header from the base64 content
                header, data = data.split(';base64,')

            # Try to decode the file. Return validation error if it fails.
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail('invalid_image')

            # Generate file name:
            file_name = str(uuid.uuid4())[:12] # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension, )

            data = ContentFile(decoded_file, name=complete_file_name)

        return super(Base64ImageField, self).to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        import imghdr

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension

class CardAppSerializer(serializers.ModelSerializer):
    """Serializer for Application"""

    class Meta:
        model = Application
        fields = ("id", "name", "status",)


class CardItemSerializer(serializers.ModelSerializer):
    """Serializer for CardItem"""
    image = Base64ImageField(
        max_length=None, use_url=True,required=False
    )

    class Meta:
        model = CardItem
        # fields = "__all__"
        exclude = ('card_data',)
    
    def create(self, validated_data):
        card_id = self.context.get("card_id")
        try:
            Card.objects.get(id=card_id)
        except:
            raise NotFound(ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card_id))
        latest_version = CardVersion.objects.filter(card__id=card_id).last()
        card_data = latest_version.card_data
        new_card_item = CardItem.objects.create(
            card_data=card_data,
            **validated_data
        )
        return new_card_item


class CardDataSerializer(serializers.ModelSerializer):
    """Serializer for CardData"""

    items = CardItemSerializer(many=True, required=False)
    image = Base64ImageField(
        max_length=None, use_url=True,required=False
    )
    class Meta:
        model = CardData
        fields = '__all__'

    def to_representation(self, instance):
        """ Add card_id to data """
        data = super().to_representation(instance)
        card_version = CardVersion.objects.all().filter(card_data=instance).first()
        data['card_id'] = card_version.card.id
      
        return data

    
    def create(self, validated_data):
        request = self.context.get("request")
        data = request.data
        items = validated_data.pop("items")
        new_card_data = CardData.objects.create(**validated_data)
        for item in items:
            CardItem.objects.create(card_data=new_card_data,**item)

        
        
        card = None
        card_id = data.get("card_id")

        if card_id:
            try:
                card = Card.objects.get(id=card_id)
            except:
                raise NotFound(detail=ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card_id))

        if card:
            latest_version = card.versions.all().order_by('-version_number').first().version_number + 1
            CardVersion.objects.create(version_number=latest_version,
                                                            card=card,
                                                            card_data=new_card_data,
                                                            )
            # card.name=data["name"]
            # card.save()
            info_logger.info(f"Create New Card Version version-{latest_version} for card  id-{card.id}, name-{card.name}")
        else:
            app_id = data.get("app_id")
            try:
                app = Application.objects.get(id=app_id)
            except:
                raise NotFound(detail=ERROR_MESSAGES["APP_ID_NOT_FOUND"].format(app_id))

            new_card = Card.objects.create(app=app,name=data["name"], type=data["type"])
            CardVersion.objects.create(version_number=1,
                                                            card=new_card,
                                                            card_data=new_card_data,
                                                            )
            info_logger.info(f"Created New Card with ID {new_card.id}")
        
        return new_card_data
    
    # def update(self, instance, validated_data):
    #     instance.header = validated_data.get('header', instance.header)
    #     instance.save()
    #     return  instance

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
        page_version = PageVersion.objects.filter(page=instance.id)
        data['versions'] = PageVersionSerializer(page_version, many = True).data
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


class PageCardDataSerializer(serializers.ModelSerializer):
    """Serializer for CardData of PageVersion"""

    items = CardItemSerializer(many=True, required=False)
    image = Base64ImageField(
        max_length=None, use_url=True,required=False
    )
    class Meta:
        model = CardData
        fields = '__all__'

    def to_representation(self, instance):
        """ Add card_id to data """
        data = super().to_representation(instance)
        card_version = CardVersion.objects.all().filter(card_data=instance).first()
        data['card_id'] = card_version.card.id
        data['card_name'] = card_version.card.name
        data['card_type'] = card_version.card.type
      
        return data


class PageCardSerializer(serializers.ModelSerializer):
    """ Serializer for Page Card Mapping"""
    
    class Meta:
        model = PageCard
        fields = ('card_pos', 'card_priority',)
        depth = 1

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['card_data'] = PageCardDataSerializer(instance.card_version.card_data).data
        return data


class PageVersionDetailSerializer(serializers.ModelSerializer):
    """Serializer for Page Version Details"""

    cards = serializers.SerializerMethodField('getPageCardMapping', required = False)

    class Meta:
        model = PageVersion
        fields = ('id', 'version_no', 'published_on', 'cards')

    def getPageCardMapping(self, obj):
        """custom serializer to get Page Card Mapping"""

        page_card = PageCard.objects.filter(page_version__id = self.instance.id)
        cards = PageCardSerializer(page_card, many = True)
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
        app_id = data.get("app_id", None)
        cards = data.get("cards", None)

        # Get app details
        try:
            app = Application.objects.get(id = app_id)
        except Exception:
            raise NotFound(ERROR_MESSAGES["APP_ID_NOT_FOUND"].format(app_id))

        # Checking cards exist or not and card is of same app
        for card in cards:
            try:
                card_query = Card.objects.get(id = card['card_id'])
            except Exception:
                raise NotFound(ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card['card_id']))
            if card_query.app != app:
                raise ValidationError(VALIDATION_ERROR_MESSAGES["CARD_APP_NOT_VALID"].format(card['card_id'], app_id))

        # Create new Page
        page = Page.objects.create(**validated_data)

        # Mapping Page and Application
        ApplicationPage.objects.create(app = app, page = page)

        # Creating Page Version
        latest_page_version = PageVersion.objects.create(page = page, version_no = 1)

        # Mapping Card Versions and Page
        for card in cards:
            card_id = card.pop('card_id')
            card_queryset = Card.objects.get(id = card_id)
            card_version = CardVersion.objects.filter(card = card_queryset).order_by('-version_number').first()
            PageCard.objects.create(page_version = latest_page_version, card_version = card_version, **card)

        return page

    def update(self, instance, validated_data):
        data = self.context.get("request").data
        cards = data.get("cards", None)

        #Getting Page is linked with which app
        app = ApplicationPage.objects.get(page = instance).app

        # Checking cards version exist or not and card is of same app
        for card in cards:
            try:
                card_query = Card.objects.get(id = card['card_id'])
            except Exception:
                raise NotFound(ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card['card_id']))
            if card_query.app != app:
                raise ValidationError(VALIDATION_ERROR_MESSAGES["CARD_APP_NOT_VALID"].format(card['card_id'], app.id))
        
        latest_version = PageVersion.objects.filter(page = instance).order_by('-version_no').first()

        if not latest_version.published_on:
            page_card = PageCard.objects.filter(page_version = latest_version)
            page_card.delete()
        else:
            latest_version = PageVersion.objects.create(page = instance, version_no = latest_version.version_no + 1)
        
        # Mapping Cards of Pages
        for card in cards:
            card_id = card.pop('card_id')
            card_queryset = Card.objects.get(id = card_id)
            card_version = CardVersion.objects.filter(card = card_queryset).order_by('-version_number').first()
            PageCard.objects.create(page_version = latest_version, card_version = card_version, **card)

        return super().update(instance, validated_data)


class PageDetailSerializer(serializers.ModelSerializer):
    """Serializer for Specific Page"""

    class Meta:
        model = Page
        fields = '__all__'

    def to_representation(self, instance):
        data =  super().to_representation(instance)
        if self.context.get('page_version'):
            data['version'] = PageVersionDetailSerializer(self.context.get('page_version')).data
        else:
            page = PageVersion.objects.select_related('page')
            page_versions = page.filter(page_id = instance.id)
            data['version'] = PageVersionSerializer(page_versions, many = True).data
        apps = ApplicationPage.objects.get(page__id = instance.id).app
        data['applications'] = PageApplicationSerializer(apps).data
        return data
    

    def update(self, instance, validated_data):
        page = Page.objects.get(id = instance.id)
        version_no = None
        if validated_data.get('active_version_no'):
            version_no = validated_data.pop('active_version_no')
        if validated_data.get('state'):
            state = validated_data.get('state')
            if state == "Published":
                instance.state = "Published"
                if version_no:
                    try:
                        page_version = PageVersion.objects.get(page = page, version_no = version_no)
                    except Exception:
                        raise NotFound(ERROR_MESSAGES["PAGE_VERSION_NOT_FOUND"].format(version_no))
                else:
                    page_version = PageVersion.objects.filter(page = page).order_by('-version_no').first()
                page_version.published_on = datetime.now()
                page_version.save()
                instance.active_version_no = page_version.version_no

            elif state == "Draft":
                instance.state = "Draft"
                instance.active_version_no = None

        return super().update(instance, validated_data)


class PageLatestDetailSerializer(serializers.ModelSerializer):
    """Serializer for Specific Page"""

    class Meta:
        model = Page
        fields = '__all__'

    def to_representation(self, instance):
        data =  super().to_representation(instance)
        data['latest_version'] = PageVersionDetailSerializer(self.context.get('version')).data
        apps = ApplicationPage.objects.get(page__id = instance.id).app
        data['applications'] = PageApplicationSerializer(apps).data
        return data