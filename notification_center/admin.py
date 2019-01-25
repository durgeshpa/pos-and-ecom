from django.contrib import admin
from notification_center.models import (
    Template, TemplateVariable, Notification,
    TextSMSActivity, VoiceCallActivity, EmailActivity,
    GCMActivity
    )
from notification_center.forms import (
    TemplateForm
    )


class TemplateAdmin(admin.ModelAdmin):
    model = Template
    form = TemplateForm
    list_display = (
        'id', 'name', 'type', 'email_alert',
        'text_sms_alert', 'voice_call_alert', 'gcm_alert'
        )
    search_fields = ('id', 'name', 'type')


class TemplateVariableAdmin(admin.ModelAdmin):
    model = TemplateVariable
    list_display = (
        'template', 'email_variable', 'text_sms_variable',
        'voice_call_variable', 'gcm_variable'
        )
    search_fields = ('id', 'template')


class TextSMSActivityAdmin(admin.TabularInline):
    model = TextSMSActivity
    fields = ['text_sms_alert', 'text_sms_sent', 'sent_at']
    readonly_fields = ['text_sms_sent', 'text_sms_alert', 'sent_at']

    # for disabling and hiding delete button from admin
    def has_delete_permission(self, request, obj=None):
        return False


class VoiceCallActivityAdmin(admin.TabularInline):
    model = VoiceCallActivity
    fields = ['voice_call_alert', 'voice_call_sent', 'sent_at']
    readonly_fields = ['voice_call_sent', 'voice_call_alert', 'sent_at']

    # for disabling and hiding delete button from admin
    def has_delete_permission(self, request, obj=None):
        return False


class EmailActivityAdmin(admin.TabularInline):
    model = EmailActivity
    fields = ['email_alert', 'email_sent', 'sent_at']
    readonly_fields = ['email_sent', 'email_alert', 'sent_at']

    # for disabling and hiding delete button from admin
    def has_delete_permission(self, request, obj=None):
        return False


class GCMActivityAdmin(admin.TabularInline):
    model = GCMActivity
    fields = ['gcm_alert', 'gcm_sent', 'sent_at']
    readonly_fields = ['gcm_sent', 'gcm_alert', 'sent_at']

    # for disabling and hiding delete button from admin
    def has_delete_permission(self, request, obj=None):
        return False


class NotificationAdmin(admin.ModelAdmin):
    model = Notification
    list_display = ('id', 'user', 'template', 'created_at')
    search_fields = ('id', 'user', 'template')
    inlines = [
        TextSMSActivityAdmin, VoiceCallActivityAdmin,
        EmailActivityAdmin, GCMActivityAdmin
    ]
    #readonly_fields = ['user', 'template']
    #for hiding object names in tabular inline
    class Media:
        css = { "all" : ("admin/css/hide_admin_inline_object_name.css",) }

admin.site.register(Template, TemplateAdmin)
admin.site.register(TemplateVariable, TemplateVariableAdmin)
admin.site.register(Notification, NotificationAdmin)
