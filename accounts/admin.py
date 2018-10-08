from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

admin.site.site_header = 'GramFactory'
admin.site.site_title = 'Admin'
admin.site.index_title = 'GramFactory'

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (_('Personal info'), {'fields': ('first_name', 'last_name',
                                         'phone_number', 'email',
                                         'password')}),
        (_('Permissions'), {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        #(_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'email', 'password1', 'password2'),
        }),
    )
    list_display = ('phone_number', 'email', 'first_name', 'last_name')
    search_fields = ('phone_number','email', 'first_name', 'last_name')
    ordering = ('email',)