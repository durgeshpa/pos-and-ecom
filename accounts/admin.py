from django.contrib import admin
from .models import User, UserDocument, AppVersion, UserWithName
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

admin.site.site_header = 'GramFactory'
admin.site.site_title = 'Admin'
admin.site.index_title = 'GramFactory'

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (_('Personal info'), {'fields': ('user_photo',('first_name', 'last_name'),
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
    list_display = ('phone_number', 'email', 'first_name', 'last_name','date_joined','imei_no')
    search_fields = ('phone_number','email', 'first_name', 'last_name')
    readonly_fields = ('user_photo_thumbnail','imei_no')
    ordering = ('email',)

@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    model = UserDocument
    fields = ( 'user_document_type','user_document_number','user_document_photo','user_document_photo_thumbnail', )
    readonly_fields = ('user_document_photo_thumbnail',)

class AppVersionAdmin(admin.ModelAdmin):
    list_display = ('app_version','update_recommended','force_update_required','created_at','modified_at')

admin.site.register(AppVersion, AppVersionAdmin)

@admin.register(UserWithName)
class UserDocumentAdmin(admin.ModelAdmin):
    model = UserWithName
    search_fields = ('phone_number','email', 'first_name', 'last_name')
