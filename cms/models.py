from django.db import models
from django.contrib.auth import get_user_model

from cms.choices import CARD_TYPE_CHOICES, SCROLL_CHOICES, STATUS_CHOICES, PAGE_STATE_CHOICES


class Application(models.Model):
    """Application Model"""
    name = models.CharField(max_length=255)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return self.name


class Card(models.Model):
    """Card Model"""
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES)
    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="cards")
    def __str__(self):
        return f"{self.name} - {self.type}"


class CardData(models.Model):
    """Card Data Model"""
    image = models.ImageField(upload_to="cards/data/images", null=True, blank=True)
    header = models.CharField(max_length=255)
    header_action = models.URLField(blank=True, null=True)
    sub_header = models.CharField(max_length=255)
    footer = models.CharField(max_length=255)
    scroll_type = models.CharField(max_length=10, choices=SCROLL_CHOICES, default="noscroll")
    is_scrollable_x = models.BooleanField(default=False)
    is_scrollable_y = models.BooleanField(default=False)
    rows = models.IntegerField(default=1)
    cols = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.id} - {self.header[0:16]}..."

class CardItem(models.Model):
    """Card Item Model"""
    card_data = models.ForeignKey(CardData, on_delete=models.CASCADE, related_name="items")
    image = models.ImageField(upload_to="cards/items/images", null=True, blank=True)
    content = models.TextField()
    priority = models.IntegerField(default=1)
    row = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.card_data.header[0:16]}..."


class CardVersion(models.Model):
    """Card Version Model"""
    version_number = models.IntegerField()
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="versions")
    card_data = models.ForeignKey(CardData, on_delete=models.CASCADE)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card.name} - {self.version_number}"


class Page(models.Model):
    """Page Model"""
    name = models.CharField(max_length=255)
    start_date = models.DateField(auto_now_add=False)
    expiry_date = models.DateField(auto_now_add=False)
    status = models.CharField(max_length=255, choices=PAGE_STATE_CHOICES, default='Draft')

    def __str__(self):
        return f"{self.name} - id {self.id}"


class PageVersion(models.Model):
    """Page Version Model"""
    version_no = models.IntegerField()
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='pages')
    created_on = models.DateTimeField(auto_now_add=True)
    published_on = models.DateTimeField(auto_now_add=False, blank=True, null=True)

    def __str__(self):
        return f"{self.page.name} - {self.version_no}"


class PageCard(models.Model):
    """Page Card Model"""
    page_version = models.ForeignKey(PageVersion, on_delete=models.CASCADE, related_name='page_versions')
    card_version = models.ForeignKey(CardVersion, on_delete=models.CASCADE, related_name='card_versions')
    card_pos = models.IntegerField()
    card_priority = models.IntegerField()

    def __str__(self):
        return f"{self.page_version.page.name} - {self.card_version.card.name}"


class ApplicationPage(models.Model):
    """Application Page Model"""
    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='apps')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='app_pages')
    state = models.CharField(max_length=255, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"{self.app.name} - {self.page.name}"

