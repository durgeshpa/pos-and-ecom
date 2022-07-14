from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from django.contrib.auth import get_user_model

from brand.models import Brand
from categories.models import Category
from cms.choices import CARD_TYPE_CHOICES, SCROLL_CHOICES, STATUS_CHOICES, PAGE_STATE_CHOICES, LANDING_PAGE_TYPE_CHOICE, \
    LISTING_SUBTYPE_CHOICE, FUNTION_TYPE_CHOICE, IMAGE_TYPE_CHOICE
from products.models import Product


class BaseTimestampUserModel(models.Model):
    """
        Abstract Model to have helper fields of created_at, created_by, updated_at and updated_by
    """
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)
    created_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Created by",
        related_name="%(app_label)s_%(class)s_created_by",
        on_delete=models.DO_NOTHING
    )
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Updated by",
        related_name="%(app_label)s_%(class)s_updated_by",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        abstract = True

class Application(BaseTimestampUserModel):
    """Application Model"""
    name = models.CharField(max_length=255)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return self.name


class Template(BaseTimestampUserModel):
    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="templates/images", null=True, blank=True)
    description = models.CharField(max_length=150, blank=True, null=True)



class Functions(BaseTimestampUserModel):
    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='Functions_app')
    name = models.CharField(max_length=20)
    type = models.PositiveIntegerField(choices=FUNTION_TYPE_CHOICE)
    url = models.CharField(max_length=200)
    required_params = ArrayField(models.CharField(max_length=200), null=True, blank=True)
    required_headers = ArrayField(models.CharField(max_length=200), null=True, blank=True)


class Card(BaseTimestampUserModel):
    """Card Model"""
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES)
    sub_type = models.PositiveSmallIntegerField(choices=LISTING_SUBTYPE_CHOICE, default=LISTING_SUBTYPE_CHOICE.LIST)
    image_data_type = models.PositiveSmallIntegerField(choices=IMAGE_TYPE_CHOICE, null=True, blank=True)
    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="cards")
    category_subtype = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='cms_cartegory_subtype', null=True, blank=True)
    brand_subtype = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='cms_brand_subtype', null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.type}"


class CardData(BaseTimestampUserModel):
    """Card Data Model"""
    image = models.ImageField(upload_to="cards/data/images", null=True, blank=True)
    header = models.CharField(max_length=255, blank=True, null=True)
    header_action = models.URLField(blank=True, null=True)
    header_action_text = models.CharField(max_length=50, blank=True, null=True)
    sub_header = models.CharField(max_length=255, null=True, blank=True)
    footer = models.CharField(max_length=255, null=True, blank=True)
    scroll_type = models.CharField(max_length=10, choices=SCROLL_CHOICES, default="noscroll")
    is_scrollable_x = models.BooleanField(default=False)
    is_scrollable_y = models.BooleanField(default=False)
    rows = models.IntegerField(default=1)
    cols = models.IntegerField(default=1)
    card_function = models.ForeignKey(Functions, on_delete=models.CASCADE, related_name="function_cards", null=True)
    params = JSONField(null=True)
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='template_cards')

    def __str__(self):
        return f"{self.id} - {self.header[0:16]}..."

class CardItem(BaseTimestampUserModel):
    """Card Item Model"""
    card_data = models.ForeignKey(CardData, on_delete=models.CASCADE, related_name="items")
    image = models.ImageField(upload_to="cards/items/images", null=True, blank=True)
    image_data_type = models.PositiveSmallIntegerField(choices=IMAGE_TYPE_CHOICE, null=True, blank=True)
    content_id = models.PositiveIntegerField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    action = models.URLField(blank=True, null=True)
    priority = models.IntegerField(default=1)
    row = models.IntegerField(default=1)
    subcategory = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True, null=True)
    subbrand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.card_data.header[0:16]}..."


class CardVersion(BaseTimestampUserModel):
    """Card Version Model"""
    version_number = models.IntegerField()
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="versions")
    card_data = models.ForeignKey(CardData, on_delete=models.CASCADE)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card.name} - {self.version_number}"


class Page(BaseTimestampUserModel):
    """Page Model"""
    name = models.CharField(max_length=255)
    start_date = models.DateField(auto_now_add=False)
    expiry_date = models.DateField(auto_now_add=False)
    state = models.CharField(max_length=255, choices=PAGE_STATE_CHOICES, default='Draft')
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='Active')
    active_version_no = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - id {self.id}"


class PageVersion(BaseTimestampUserModel):
    """Page Version Model"""
    version_no = models.IntegerField()
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='pages')
    created_on = models.DateTimeField(auto_now_add=True)
    published_on = models.DateTimeField(auto_now_add=False, blank=True, null=True)

    def __str__(self):
        return f"{self.page.name} - {self.version_no}"


class PageCard(BaseTimestampUserModel):
    """Page Card Model"""
    page_version = models.ForeignKey(PageVersion, on_delete=models.CASCADE, related_name='page_versions')
    card_version = models.ForeignKey(CardVersion, on_delete=models.CASCADE, related_name='card_versions')
    card_pos = models.IntegerField()
    card_priority = models.IntegerField()

    def __str__(self):
        return f"{self.page_version.page.name} - {self.card_version.card.name}"


class ApplicationPage(BaseTimestampUserModel):
    """Application Page Model"""
    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='apps')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='app_pages')
    state = models.CharField(max_length=255, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"{self.app.name} - {self.page.name}"


class LandingPage(BaseTimestampUserModel):
    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='app_landing_pages')
    name = models.CharField(max_length=20)
    type = models.PositiveIntegerField(choices=LANDING_PAGE_TYPE_CHOICE)
    sub_type = models.PositiveIntegerField(choices=LISTING_SUBTYPE_CHOICE)
    banner_image = models.ImageField(upload_to="cards/items/images", null=True, blank=True)
    page_function = models.ForeignKey(Functions, on_delete=models.CASCADE, null=True, related_name='function_pages')
    params = JSONField(null=True)



class LandingPageProducts(BaseTimestampUserModel):
    landing_page = models.ForeignKey(LandingPage, on_delete=models.CASCADE, related_name='landing_page_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_landing_pages')

