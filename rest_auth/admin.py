from django.contrib import admin
from .models import *


class TokenAdmin(admin.ModelAdmin):
    list_display = [
        'key', 'user', 'created'
    ]
    fields = ['key', 'user']
    readonly_fields = ['key']

# Register your models here.
admin.site.register(Token, TokenAdmin)
