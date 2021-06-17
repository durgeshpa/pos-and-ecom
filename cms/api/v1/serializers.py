import logging
from datetime import datetime
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from ...models import CardData, Card, CardVersion, CardItem, Application, Page, PageCard, PageVersion, ApplicationPage

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.

    Heavily based on
    https://github.com/tomchristie/django-rest-framework/pull/1268

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


class CardDataSerializer(serializers.ModelSerializer):
    """Serializer for CardData"""

    items = CardItemSerializer(many=True)
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
        app_id = data.get("app_id")
        items = validated_data.pop("items")
        new_card_data = CardData.objects.create(**validated_data)
        for item in items:
            print(item)
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
        app_id = data.get("app_id")
        cards = data.get("cards")
        # Get app details
        app = get_object_or_404(Application, id = app_id)
        # Checking page exist with name and app
        app_page = ApplicationPage.objects.select_related('page').filter(app = app)
        page = app_page.filter(page__name = data.get("name")).first()
        if page:
            page = page.page
            latest_page_version = PageVersion.objects.filter(page = page).order_by('-version_no').first()
            if page.state == 'Draft':
                PageCard.objects.filter(page_version = latest_page_version).delete()
            else:
                latest_page_version = PageVersion.objects.create(page = page, version_no = latest_page_version.version_no + 1)
                page.state = "Draft"
                page.save()
        else:
            # Create new Page
            page = Page.objects.create(**validated_data)
            # Mapping Page and Application
            app = get_object_or_404(Application, id = app_id)
            ApplicationPage.objects.create(app = app, page = page)
            # Creating Page Version
            latest_page_version = PageVersion.objects.create(page = page, version_no = 1)
        # Mapping Cards of Pages
        for card in cards:
           PageCard.objects.create(page_version = latest_page_version, **card)
        return page


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
    

    def update(self, instance, validated_data):
        page = Page.objects.get(id = instance.id)
        if validated_data.get('state'):
            state = validated_data.get('state')
            if state == "Published":
                instance.state = "Published"
                if validated_data.get('active_version_no'):
                    instance.active_version_no = validated_data.get('active_version_no')
                else:
                    page_version = PageVersion.objects.filter(page = page).order_by('-version_no').first()
                    page_version.published_on = datetime.now()
                    page_version.save()
                    instance.active_version_no = page_version.version_no
        return super().update(instance, validated_data)