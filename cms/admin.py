from django.contrib import admin
from cms.models import Card, CardVersion, CardData, CardItem, Application, ApplicationPage, Page, PageVersion, PageCard

admin.site.register(Application)
admin.site.register(ApplicationPage)
admin.site.register(Card)
admin.site.register(CardVersion)
admin.site.register(CardData)
admin.site.register(CardItem)
admin.site.register(Page)
admin.site.register(PageVersion)
admin.site.register(PageCard)