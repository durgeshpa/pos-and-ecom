import logging
import urllib
from datetime import datetime

from django.db import transaction
from django.db.models import OuterRef, Exists, Q
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound, ValidationError

from global_config.views import get_config
from pos.models import RetailerProduct
from products.models import Product, SuperStoreProductPrice, ParentProduct
from retailer_backend.common_function import isBlank
from ...choices import LANDING_PAGE_TYPE_CHOICE, LISTING_SUBTYPE_CHOICE, FUNTION_TYPE_CHOICE, \
    CARD_TYPE_PRODUCT, CARD_TYPE_CAREGORY, CARD_TYPE_BRAND, CARD_TYPE_IMAGE, IMAGE_TYPE_CHOICE, LIST, RETAILER, \
    SUPERSTORE, INDEX_TYPE_ONE, INDEX_TYPE_THREE, ECOMMERCE, APP_TYPE_CHOICE
from ...common_functions import check_inventory, isEmptyString
from ...models import CardData, Card, CardVersion, CardItem, Application, Page, PageCard, PageVersion, ApplicationPage, \
    LandingPage, Functions, LandingPageProducts, Template
from cms.messages import VALIDATION_ERROR_MESSAGES, ERROR_MESSAGES
from categories.models import Category
from brand.models import Brand

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
            file_name = str(uuid.uuid4())[:12]  # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension,)

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


class ChoicesSerializer(serializers.ChoiceField):

    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return {'id': obj, 'description': self._choices[obj]}

class ChoicesValueSerializer(serializers.ChoiceField):
    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return  self._choices[obj]

class CardItemSerializer(serializers.ModelSerializer):
    """Serializer for CardItem"""
    image = Base64ImageField(
        max_length=None, use_url=True, required=False, allow_null=True
    )
    item_content = serializers.SerializerMethodField()
    def get_item_content(self, obj):
        if not self.context.get('card', None):
            return obj.content
        card = self.context['card']
        try:
            if card.type == CARD_TYPE_PRODUCT:
                return ProductSerializer(Product.objects.get(id=obj.content_id), context=self.context).data
            elif card.type == CARD_TYPE_CAREGORY:
                return CategorySerializer(Category.objects.get(id=obj.content_id)).data
            elif card.type == CARD_TYPE_BRAND:
                return BrandSerializer(Brand.objects.get(id=obj.content_id)).data
        except Exception as e:
            info_logger.error(e)
            info_logger.error(f"CardItemSerializer | get_content | Failed to create content for CardItem {obj.id}")
        return obj.content

    def to_internal_value(self, data):
        image = data.get('image', None)
        if image == '':
            data.pop('image')
        return super(CardItemSerializer, self).to_internal_value(data)

    class Meta:
        model = CardItem
        fields = ('id', 'image', 'content_id', 'content', 'item_content', 'action', 'priority', 'row', 'subcategory',
                  'subbrand', 'image_data_type')

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


def get_index_type(app):
    if app.name in [RETAILER, SUPERSTORE]:
        index_type = INDEX_TYPE_ONE
    else:
        index_type = INDEX_TYPE_THREE
    return index_type


def make_cms_item_redirect_url(request, card_type, image_data_type, app):
    index_type = get_index_type(app)
    search_url = "/retailer/sp/api/v1/GRN/search/?index_type="
    switcher = {
        "product": "/product/api/v1/child-product/?product_type=0&id=",
        "category": "/category/api/v1/category/?id=",
        "brand": "/brand/api/v1/brand/?id=",
        "image": {
            1: "/product/api/v1/child-product/?product_type=0&id=",
            2: search_url + index_type + "&search_type=1&&categories=",
            3: search_url + index_type + "&search_type=1&brands=",
            4: "/cms/api/v1/landing-pages/?id=",
            5: search_url + index_type + "&search_type=1&&categories=",
        },
        "text": search_url + index_type + "&search_type=1&keyword="
    }
    if not isinstance(switcher.get(card_type), str):
        return switcher.get(card_type).get(image_data_type)
    return switcher.get(card_type)


class ApplicationSerializerForTemplate(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ('id', 'name')


class TemplateSerializer(serializers.ModelSerializer):
    app = ApplicationSerializerForTemplate(read_only=True)

    class Meta:
        model = Template
        fields = ('id', 'app', 'name', 'image', 'description')

    def validate(self, data):
        if 'name' not in self.initial_data or isEmptyString(self.initial_data['name']) is None:
            raise serializers.ValidationError('Template Name is required.')
        elif 'app' not in self.initial_data or self.initial_data['app'] is None:
            raise serializers.ValidationError('Application is required.')
        elif not Application.objects.filter(id=self.initial_data['app']).exists():
            raise serializers.ValidationError('Invalid App ID.')
        elif Template.objects.filter(name=self.initial_data['name'].strip().upper(),
                                     app_id=self.initial_data['app']).exists():
            raise serializers.ValidationError('Template already exists')
        data['app_id'] = self.initial_data['app']
        data['name'] = self.initial_data['name'].strip().upper()
        return data


class CardDataSerializer(serializers.ModelSerializer):
    """Serializer for CardData"""
    items = CardItemSerializer(many=True, required=False)
    image = Base64ImageField(
        max_length=None, use_url=True, required=False, allow_null=True
    )

    class Meta:
        model = CardData
        fields = '__all__'

    def to_internal_value(self, data):
        image = data.get('image', None)
        if image == '':
            data.pop('image')
        return super(CardDataSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        """ Add card_id to data """
        data = super().to_representation(instance)
        card_version = CardVersion.objects.all().filter(card_data=instance).first()
        data['card_id'] = card_version.card.id
        data['template'] = TemplateSerializer(instance.template).data
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        data = request.data
        items = validated_data.pop("items")
        card = None
        card_id = data.get("card_id")

        if card_id:
            try:
                card = Card.objects.get(id=card_id)
            except:
                raise NotFound(detail=ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card_id))

        new_card_data = CardData.objects.create(**validated_data)
        if card:
            latest_version = card.versions.all().order_by('-version_number').first().version_number + 1
            CardVersion.objects.create(version_number=latest_version,
                                       card=card,
                                       card_data=new_card_data,
                                       )
            app = card.app
            info_logger.info(
                f"Create New Card Version version-{latest_version} for card  id-{card.id}, name-{card.name}")
        else:
            app_id = data.get("app_id")
            try:
                app = Application.objects.get(id=app_id)
                data['app'] = app
            except:
                raise NotFound(detail=ERROR_MESSAGES["APP_ID_NOT_FOUND"].format(app_id))
            if data.get('category_subtype'):
                category = Category.objects.get(id=data['category_subtype'])
                data['category_subtype'] = category
            elif data.get('brand_subtype'):
                brand = Brand.objects.get(id=data['brand_subtype'])
                data['brand_subtype'] = brand
            card = Card.objects.create(**data)
            CardVersion.objects.create(version_number=1,
                                       card=card,
                                       card_data=new_card_data,
                                       )
            info_logger.info(f"Created New Card with ID {card.id}")

        for item in items:
            image_data_type = item.get('image_data_type', None)
            redirect_url_base = make_cms_item_redirect_url(request, card.type, image_data_type, app)
            if card.type == "text":
                item['action'] = request.build_absolute_uri(redirect_url_base + str(item['content']))
            else:
                item['action'] = request.build_absolute_uri(redirect_url_base + str(item['content_id']))
            CardItem.objects.create(card_data=new_card_data, **item)

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
    created_by = UserSerializer(required=False)

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
        data['versions'] = PageVersionSerializer(page_version, many=True).data
        return data


class ApplicationDataSerializer(serializers.ModelSerializer):
    """Specific Application Serializer"""
    created_by = UserSerializer()

    class Meta:
        model = Application
        fields = ('id', 'name', 'created_on', 'status', 'created_by')

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


class PageFunctionSerializer(serializers.ModelSerializer):
    type = ChoicesSerializer(choices=FUNTION_TYPE_CHOICE)

    class Meta:
        model = Functions
        fields = ('id', 'type', 'name', 'url', 'required_params', 'required_headers', 'app')

    def validate(self, data):

        if 'name' not in self.initial_data or isBlank(self.initial_data['name']):
            raise serializers.ValidationError("'name' | This is required")
        elif 'type' not in self.initial_data and self.initial_data.get('type'):
            raise serializers.ValidationError("'type' | This is required")
        elif 'url' not in self.initial_data or isBlank(self.initial_data.get('url')):
            raise serializers.ValidationError("'url' | This is required")
        elif self.initial_data.get('required_params') and not isinstance(self.initial_data['required_params'], list):
            raise serializers.ValidationError("'required_params' | Only list type is supported")
        elif self.initial_data.get('required_headers') and not isinstance(self.initial_data['required_headers'], list):
            raise serializers.ValidationError("'required_headers' | Only list type is supported")
        elif Functions.objects.filter(type=self.initial_data['type'], name=self.initial_data['name'].strip()).exists():
            raise serializers.ValidationError(f"Function already exists")
        data['name'] = self.initial_data['name'].strip()
        data['type'] = self.initial_data['type']
        data['url'] = self.initial_data['url'].strip()
        data['required_params'] = self.initial_data['required_params']
        data['required_headers'] = self.initial_data['required_headers']

        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            function = Functions.objects.create(**validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return function

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            function = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return function


class PageCardDataSerializer(serializers.ModelSerializer):
    """Serializer for CardData of PageVersion"""
    items = serializers.SerializerMethodField()
    # items = CardItemSerializer(many=True, required=False)
    image = Base64ImageField(
        max_length=None, use_url=True, required=False
    )
    card_function = PageFunctionSerializer(read_only=True)

    class Meta:
        model = CardData
        fields = '__all__'

    def get_items(self, obj):
        shop_id = self.context.get('shop_id', None)
        card = self.context.get('card', None)
        if shop_id and card and ((card.type == CARD_TYPE_PRODUCT and card.sub_type == LISTING_SUBTYPE_CHOICE.LIST)
                                 or (
                                         card.type == CARD_TYPE_IMAGE and card.image_data_type == IMAGE_TYPE_CHOICE.PRODUCT)):
            sub_query = RetailerProduct.objects.filter(linked_product_id=OuterRef('content_id'), shop_id=shop_id,
                                                       is_deleted=False, online_enabled=True)
            superstore_query = Product.objects.filter(id=OuterRef('content_id'), status='active',
                                                      parent_product__product_type=ParentProduct.SUPERSTORE,
                                                      super_store_product_price__isnull=False,
                                                      super_store_product_price__seller_shop__parrent_mapping__retailer_id=shop_id)
            card_items = obj.items.annotate(retailer_product_exists=Exists(sub_query),
                                            superstore_product_exists=Exists(superstore_query))

            retailer_items = card_items.filter(retailer_product_exists=True)
            superstore_items = card_items.filter(superstore_product_exists=True)
            items = check_inventory(retailer_items, shop_id)
            items = items.union(superstore_items)
            return CardItemSerializer(items, many=True, context=self.context).data
        return CardItemSerializer(obj.items, many=True, context=self.context).data

    def to_representation(self, instance):
        """ Add card_id to data """
        data = super().to_representation(instance)
        card_version = CardVersion.objects.all().filter(card_data=instance).first()
        data['card_id'] = card_version.card.id
        data['card_name'] = card_version.card.name
        data['card_type'] = card_version.card.type
        data['card_sub_type'] = card_version.card.get_sub_type_display()
        data['template'] = card_version.card_data.template.name
        data['image_data_type'] = card_version.card.get_image_data_type_display()
        return data


class PageCardSerializer(serializers.ModelSerializer):
    """ Serializer for Page Card Mapping"""

    class Meta:
        model = PageCard
        fields = ('card_pos', 'card_priority')
        depth = 1

    def to_representation(self, instance):
        data = super().to_representation(instance)
        card_version = CardVersion.objects.filter(card=instance.card_version.card).last()
        self.context['card'] = card_version.card
        data['card_data'] = PageCardDataSerializer(card_version.card_data, context=self.context).data
        return data


class PageVersionDetailSerializer(serializers.ModelSerializer):
    """Serializer for Page Version Details"""

    cards = serializers.SerializerMethodField('getPageCardMapping', required=False)

    class Meta:
        model = PageVersion
        fields = ('id', 'version_no', 'published_on', 'cards')

    def getPageCardMapping(self, obj):
        """custom serializer to get Page Card Mapping"""

        page_card = PageCard.objects.filter(page_version__id=self.instance.id)
        cards = PageCardSerializer(page_card, many=True, context=self.context)
        return cards.data


class PageSerializer(serializers.ModelSerializer):
    """Page Serializer"""

    class Meta:
        model = Page
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        page_version = PageVersion.objects.filter(page=instance.id)
        data['version'] = PageVersionSerializer(page_version, many=True).data
        app = ApplicationPage.objects.select_related('app').get(page=instance.id).app
        data['application'] = PageApplicationSerializer(app).data
        return data

    def create(self, validated_data):
        data = self.context.get("request").data
        app_id = data.get("app_id", None)
        cards = data.get("cards", None)

        # Get app details
        try:
            app = Application.objects.get(id=app_id)
        except Exception:
            raise NotFound(ERROR_MESSAGES["APP_ID_NOT_FOUND"].format(app_id))

        # Checking cards exist or not and card is of same app
        for card in cards:
            try:
                card_query = Card.objects.get(id=card['card_id'])
            except Exception:
                raise NotFound(ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card['card_id']))
            if card_query.app != app:
                raise ValidationError(VALIDATION_ERROR_MESSAGES["CARD_APP_NOT_VALID"].format(card['card_id'], app_id))

        # Create new Page
        page = Page.objects.create(**validated_data)

        # Mapping Page and Application
        ApplicationPage.objects.create(app=app, page=page)

        # Creating Page Version
        latest_page_version = PageVersion.objects.create(page=page, version_no=1)

        # Mapping Card Versions and Page
        for card in cards:
            card_id = card.pop('card_id')
            card_queryset = Card.objects.get(id=card_id)
            card_version = CardVersion.objects.filter(card=card_queryset).order_by('-version_number').first()
            PageCard.objects.create(page_version=latest_page_version, card_version=card_version, **card)

        return page

    def update(self, instance, validated_data):
        data = self.context.get("request").data
        cards = data.get("cards", None)

        # Getting Page is linked with which app
        app = ApplicationPage.objects.get(page=instance).app

        # Checking cards version exist or not and card is of same app
        for card in cards:
            try:
                card_query = Card.objects.get(id=card['card_id'])
            except Exception:
                raise NotFound(ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card['card_id']))
            if card_query.app != app:
                raise ValidationError(VALIDATION_ERROR_MESSAGES["CARD_APP_NOT_VALID"].format(card['card_id'], app.id))

        latest_version = PageVersion.objects.filter(page=instance).order_by('-version_no').first()

        if not latest_version.published_on:
            page_card = PageCard.objects.filter(page_version=latest_version)
            page_card.delete()
        else:
            latest_version = PageVersion.objects.create(page=instance, version_no=latest_version.version_no + 1)

        # Mapping Cards of Pages
        for card in cards:
            card_id = card.pop('card_id')
            card_queryset = Card.objects.get(id=card_id)
            card_version = CardVersion.objects.filter(card=card_queryset).order_by('-version_number').first()
            PageCard.objects.create(page_version=latest_version, card_version=card_version, **card)

        return super().update(instance, validated_data)


class PageDetailSerializer(serializers.ModelSerializer):
    """Serializer for Specific Page"""

    class Meta:
        model = Page
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get('page_version'):
            data['version'] = PageVersionDetailSerializer(self.context.get('page_version')).data
        else:
            page = PageVersion.objects.select_related('page')
            page_versions = page.filter(page_id=instance.id)
            data['version'] = PageVersionSerializer(page_versions, many=True).data
        apps = ApplicationPage.objects.filter(page__id=instance.id).last().app
        data['applications'] = PageApplicationSerializer(apps).data
        return data

    def update(self, instance, validated_data):
        page = Page.objects.get(id=instance.id)
        version_no = None
        if validated_data.get('active_version_no'):
            version_no = validated_data.pop('active_version_no')
        if validated_data.get('state'):
            state = validated_data.get('state')
            if state == "Published":
                instance.state = "Published"
                if version_no:
                    try:
                        page_version = PageVersion.objects.get(page=page, version_no=version_no)
                    except Exception:
                        raise NotFound(ERROR_MESSAGES["PAGE_VERSION_NOT_FOUND"].format(version_no))
                else:
                    page_version = PageVersion.objects.filter(page=page).order_by('-version_no').first()
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
        data = super().to_representation(instance)
        apps = ApplicationPage.objects.get(page__id=instance.id).app
        data['applications'] = PageApplicationSerializer(apps).data
        data['latest_version'] = PageVersionDetailSerializer(self.context.pop('version'), context=self.context).data
        return data


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for category data
    """

    class Meta:
        model = Category
        fields = ('id', 'category_name')


class SubCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for subcategory with banner
    """
    banner_image = serializers.SerializerMethodField()

    def get_banner_image(self, obj):
        if obj.banner_subcategory.filter(status=True).exists():
            return obj.banner_subcategory.filter(status=True).last().image.url
        else:
            return None

    class Meta:
        model = Category
        fields = ('category_name', 'id', 'banner_image')


class BrandSerializer(serializers.ModelSerializer):
    """
    Serializer for brand data
    """

    class Meta:
        model = Brand
        fields = ('id', 'brand_name')


class SubBrandSerializer(serializers.ModelSerializer):
    """
    Serializer for subbrand with banner
    """
    banner_image = serializers.SerializerMethodField()

    def get_banner_image(self, obj):
        if obj.banner_subbrand.filter(status=True).exists():
            return obj.banner_subbrand.filter(status=True).last().image.url
        else:
            return None

    class Meta:
        model = Brand
        fields = ('brand_name', 'id', 'banner_image')


class ProductImageSerializer(serializers.Serializer):
    class Meta:
        fields = ('image_name', 'image_url')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image_name'] = instance.image_name
        data['image_url'] = instance.image.url
        return data


class ProductSerializer(serializers.ModelSerializer):
    product_images = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    online_price = serializers.SerializerMethodField()
    brand_id = serializers.SerializerMethodField()
    category_id = serializers.SerializerMethodField()
    sub_category = serializers.SerializerMethodField()
    sub_category_id = serializers.SerializerMethodField()
    super_store_product_selling_price = serializers.SerializerMethodField()
    off_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'online_price', 'product_images', 'category', 'category_id', 'brand', 'brand_id',
                  'sub_category', 'sub_category_id', 'super_store_product_selling_price', 'off_percentage')

    def get_product_images(self, obj):
        images = obj.product_pro_image.all()
        if not images:
            parent_product = obj.parent_product
            if parent_product:
                images = parent_product.parent_product_pro_image.all()
        return ProductImageSerializer(images, many=True).data

    def get_brand(self, obj):
        try:
            brand = str(obj.product_brand)
            return brand if brand else ''
        except:
            return ''

    def get_category(self, obj):
        try:
            category = [str(c.category) for c in
                        obj.parent_product.parent_product_pro_b2c_category.filter(status=True)]
            return category if category else ''
        except:
            return ''

    def get_brand_id(self, obj):
        try:
            brand_id = str(obj.product_brand.id)
            return brand_id if brand_id else ''
        except:
            return ''

    def get_category_id(self, obj):
        try:
            category_id = [str(c.category_id) for c in
                           obj.parent_product.parent_product_pro_b2c_category.filter(status=True)]
            return category_id if category_id else ''
        except:
            return ''

    def get_sub_category(self, obj):
        try:
            category = [str(c.category) for c in
                        obj.parent_product.parent_product_pro_b2c_category.filter(status=True)]
            return category if category else ''
        except:
            return ''

    def get_sub_category_id(self, obj):
        try:
            category_id = [str(c.category_id) for c in
                           obj.parent_product.parent_product_pro_b2c_category.filter(status=True)]
            return category_id if category_id else ''
        except:
            return ''

    def get_online_price(self, obj):
        retailer_product = RetailerProduct.objects.filter(linked_product_id=obj.id, status='active',
                                                          online_enabled=True)
        if retailer_product.exists():
            return retailer_product.last().online_price
        return None

    def get_super_store_product_selling_price(self, obj):
        seller_shop = self.context.get('parent_shop')
        if seller_shop:
            superstore_price = SuperStoreProductPrice.objects.filter(product_id=obj.id,
                                                                     seller_shop=seller_shop)
            if superstore_price.exists():
                return superstore_price.last().selling_price
        return None

    def get_off_percentage(self, obj):
        parent_shop_id = self.context.get('parent_shop')
        price = obj.get_superstore_price_by_shop(parent_shop_id) if parent_shop_id else None
        return round(100 - ((price.selling_price * 100) / obj.product_mrp)) if price else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['name'] = instance.product_name
        data['ean'] = instance.product_ean_code
        data['mrp'] = instance.product_mrp
        return data


class LandingPageProductSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()

    def get_product(self, obj):
        return ProductSerializer(obj.product, context=self.context).data

    class Meta:
        model = LandingPageProducts
        fields = ('product',)


class LandingPageSerializer(serializers.ModelSerializer):
    app = ApplicationSerializer(read_only=True)
    type = ChoicesSerializer(choices=LANDING_PAGE_TYPE_CHOICE, required=True)
    sub_type = ChoicesSerializer(choices=LISTING_SUBTYPE_CHOICE, required=True)
    page_function = PageFunctionSerializer(read_only=True)
    page_action_url = serializers.SerializerMethodField()
    page_link = serializers.SerializerMethodField()
    banner_image = Base64ImageField(max_length=None, use_url=True, required=False, allow_null=True)
    landing_page_products = serializers.SerializerMethodField()

    def to_internal_value(self, data):
        banner_image = data.get('banner_image', None)
        if banner_image == '':
            data.pop('banner_image')
        return super(LandingPageSerializer, self).to_internal_value(data)

    def get_landing_page_products(self, obj):
        shop_id = self.context.get('shop_id', None)
        app_id = self.context.get('app_id', None)
        items = obj.landing_page_products
        if app_id and app_id == APP_TYPE_CHOICE.ECOMMERCE and shop_id:
            sub_query = RetailerProduct.objects.filter(linked_product_id=OuterRef('product_id'), shop_id=shop_id,
                                                       is_deleted=False, online_enabled=True)
            items = check_inventory(obj.landing_page_products.annotate(retailer_product_exists=Exists(sub_query))

                                                                   .filter(retailer_product_exists=True), shop_id)
        return LandingPageProductSerializer(items, many=True, context=self.context).data

    def get_page_action_url(self, obj):
        if obj.page_function:
            if not obj.params:
                return obj.page_function.url
            return obj.page_function.url + "?" + urllib.parse.urlencode(obj.params)

    def get_page_link(self, obj):
        request = self.context.get('request')
        if request:
            request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
            return request.build_absolute_uri('/cms/api/v1/landing-pages/?id=' + str(obj.id))

    class Meta:
        model = LandingPage
        fields = ('id', 'name', 'banner_image', 'app', 'type', 'sub_type', 'page_function', 'params', 'page_action_url',
                  'landing_page_products', 'page_link')

    def validate(self, data):
        if 'id' not in self.initial_data:
            if 'app' not in self.initial_data or self.initial_data.get('app') is None:
                raise serializers.ValidationError("'app' | This is required")
            elif int(self.initial_data['app']) not in Application.objects.values_list('pk', flat=True):
                raise serializers.ValidationError(f"Invalid app {self.initial_data['app']}")
            elif 'name' not in self.initial_data or isBlank(self.initial_data.get('name')):
                raise serializers.ValidationError("'name' | This is required")
            elif 'type' not in self.initial_data or not self.initial_data.get('type'):
                raise serializers.ValidationError("'type' | This is required")
            elif int(self.initial_data['type']) not in get_config('CMS_LANDING_PAGE_TYPE', LANDING_PAGE_TYPE_CHOICE):
                raise serializers.ValidationError(f"Invalid landing page type selected{self.initial_data['type']}")
            elif 'sub_type' not in self.initial_data or not self.initial_data.get('sub_type'):
                raise serializers.ValidationError("'type' | This is required")
            elif int(self.initial_data['sub_type']) not in get_config('CMS_LANDING_PAGE_SUBTYPE',
                                                                      LISTING_SUBTYPE_CHOICE):
                raise serializers.ValidationError(
                    f"Invalid landing page sub type selected{self.initial_data['sub_type']}")
            elif int(self.initial_data['sub_type']) == LISTING_SUBTYPE_CHOICE.LIST:
                validation_result = self.validate_landing_page_products()
                if 'error' in validation_result:
                    raise serializers.ValidationError(validation_result['error'])
                data['products'] = validation_result['data']
            elif int(self.initial_data['sub_type']) == LISTING_SUBTYPE_CHOICE.FUNCTION:
                validation_result = self.validate_landing_page_function()
                if 'error' in validation_result:
                    raise serializers.ValidationError(validation_result['error'])
                data['page_function'] = validation_result['data']
                data['params'] = self.initial_data.get('params')

            if LandingPage.objects.filter(name=self.initial_data['name'].strip()).exists():
                raise serializers.ValidationError("Landing page already exists for this name.")
        elif 'id' in self.initial_data and self.initial_data['id']:
            if 'app' in self.initial_data and self.initial_data['app'] != self.instance.app_id:
                raise serializers.ValidationError("Updating app is not allowed.")
            elif 'type' in self.initial_data and self.initial_data['type'] != self.instance.type:
                raise serializers.ValidationError("Updating type is not allowed.")
            elif 'sub_type' in self.initial_data and self.initial_data['sub_type'] != self.instance.sub_type:
                raise serializers.ValidationError("Updating sub_type is not allowed.")
            elif self.instance.sub_type == LISTING_SUBTYPE_CHOICE.LIST:
                validation_result = self.validate_landing_page_products()
                if 'error' in validation_result:
                    raise serializers.ValidationError(validation_result['error'])
                data['products'] = validation_result['data']
            elif int(self.initial_data['sub_type']) == LISTING_SUBTYPE_CHOICE.FUNCTION:
                validation_result = self.validate_landing_page_function()
                if 'error' in validation_result:
                    raise serializers.ValidationError(validation_result['error'])
                data['page_function'] = validation_result['data']
                data['params'] = self.initial_data.get('params')

        data['name'] = self.initial_data['name'].strip()
        data['app_id'] = int(self.initial_data['app'])
        data['type'] = int(self.initial_data['type'])
        data['sub_type'] = int(self.initial_data['sub_type'])

        return data

    def validate_landing_page_products(self):
        if not self.initial_data.get('products') or not isinstance(self.initial_data.get('products'), list) \
                or len(self.initial_data.get('products')) == 0:
            return {'error': "List of items is required for List type landing page"}
        products = []
        for product_id in self.initial_data['products']:
            if not Product.objects.filter(pk=int(product_id)).exists():
                raise serializers.ValidationError(f"Product with id {product_id} does not exists")
            products.append(Product.objects.get(pk=product_id))
        return {'data': products}

    def validate_landing_page_function(self):
        if self.initial_data.get('page_function') is None:
            return {'error': "'function' | This is required."}
        elif int(self.initial_data['page_function']) not in \
                Functions.objects.filter(type=self.initial_data['type']).values_list('pk', flat=True):
            return {'error': "Invalid function selected."}
        func = Functions.objects.filter(pk=self.initial_data['page_function']).last()
        if func.required_params and len(func.required_params) > 0:
            for param in func.required_params:
                if not self.initial_data.get('params') or param not in self.initial_data.get('params') or \
                        self.initial_data['params'][param] is None:
                    return {'error': f'{param} is missing in params'}
        return {'data': func}

    @transaction.atomic
    def create(self, validated_data):
        try:
            product_list = None
            if validated_data.get('products') is not None:
                product_list = validated_data.pop('products')
            landing_page = LandingPage.objects.create(**validated_data)
            if product_list:
                LandingPageProducts.objects.bulk_create([
                    LandingPageProducts(landing_page=landing_page, product=p, created_by=validated_data['created_by'])
                    for p in product_list],
                    batch_size=None)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return landing_page

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            product_list = validated_data.pop('products', None)
            landing_page = super().update(instance, validated_data)
            if product_list:
                landing_page.landing_page_products.all().delete()
                LandingPageProducts.objects.bulk_create([LandingPageProducts(landing_page=landing_page, product=p,
                                                                             created_by=validated_data['updated_by'],
                                                                             updated_by=validated_data['updated_by'])
                                                         for p in product_list],
                                                        batch_size=None)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        return landing_page
