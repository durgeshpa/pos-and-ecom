from django.contrib import admin
from .models import *
from admin_auto_filters.filters import AutocompleteFilter
from django.db.models import Q


class TokenFilter(AutocompleteFilter):
    title = 'User'  # display title
    field_name = 'user'  # name of the foreign key field

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(user_id=self.value())
            )


class TokenAdmin(admin.ModelAdmin):
    list_display = [
        'key', 'user', 'created'
    ]
    fields = ['key', 'user']
    readonly_fields = ['key']
    list_filter = [TokenFilter, ]

# Register your models here.
admin.site.register(Token, TokenAdmin)
