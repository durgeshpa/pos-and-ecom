from django.contrib import admin
from cms.models import Card, CardVersion, CardData, CardItem, Application

admin.site.register(Application)

admin.site.register(Card)
admin.site.register(CardVersion)
admin.site.register(CardData)
admin.site.register(CardItem)