from django.contrib import admin
from django.contrib.auth import get_user_model
from django.conf.urls import url

from notification_center.models import (
    Template, TemplateVariable, Notification, UserNotification,
    TextSMSActivity, VoiceCallActivity, EmailActivity,
    GCMActivity, NotificationScheduler, GroupNotificationScheduler
    )
from notification_center.forms import (
    TemplateForm, GroupNotificationForm
    )
from notification_center.utils import (
    SendNotification
    )
from notification_center.views import (
    group_notification_view
    )

User = get_user_model()

from celery import Celery
from celery.schedules import crontab
app = Celery()

@app.on_after_configure.connect
def setup_periodic_tasks(sender=None, **kwargs):
    # This function is used to setup tasks via celery
    import pdb; pdb.set_trace()
    # data = kwargs['data']
    # Calls test('hello') every 10 seconds.
    sender.add_periodic_task(10.0, test.s('hello'), name='add every 10')

    # Calls test('world') every 30 seconds
    sender.add_periodic_task(30.0, test.s('world'), expires=10)

    # Executes every Monday morning at 7:30 a.m.
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1),
        test.s('Happy Mondays!'),
    )

@app.task
def test(arg):
    print(arg)

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
    list_display = ['send_sms_notification']

    def send_sms_notification():
        try:
            #user_instance = User.objects.get(id=obj.user.id)
            
            # code to send notification
            SendNotification(user_id=1, activity_type="SIGNUP").send_notification()
        except Exception as e:
            print (e.args)
            pass

    send_sms_notification.short_description = 'Send SMS Notification'

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


class UserNotificationAdmin(admin.ModelAdmin):
    model = UserNotification
    #fields = '__all__'


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

    # def save_model(self, request, obj, form, change):
    #     try:
    #         user_instance = User.objects.get(id=obj.user.id)
    #         # code to send notification
    #         SendNotification().send_notification()
    #     except Exception as e:
    #         print (e.args)
    #         pass
    #     super(Notification, self).save_model(request, obj, form, change)    

    class Media:
        css = { "all" : ("admin/css/hide_admin_inline_object_name.css",) }



class NotificationSchedulerAdmin(admin.ModelAdmin):
    model = NotificationScheduler
    list_display = ('id', 'user', 'template', 'run_at', 'repeat', 'created_at')
    search_fields = ('id', 'user', 'template')
    # inlines = [
    #     TextSMSActivityAdmin, VoiceCallActivityAdmin,
    #     EmailActivityAdmin, GCMActivityAdmin
    # ]
    #readonly_fields = ['user', 'template']
    #for hiding object names in tabular inline

    def save_model(self, request, obj, form, change):
        try:
            #import pdb; pdb.set_trace()
            #integrate with celery beat
            user_id = User.objects.get(id=obj.user.id).id
            activity_type = Template.objects.get(id=obj.template.id).type
            # code to send notification
            #setup_periodic_tasks()  #data = {}
            data = {}
            data['test'] = "test"

            #setup_periodic_tasks()

            SendNotification(user_id=user_id, activity_type=activity_type).send()
        except Exception as e:
            print (e.args)
            pass
        super(NotificationSchedulerAdmin, self).save_model(request, obj, form, change)    


class GroupNotificationSchedulerAdmin(admin.ModelAdmin):
    model = GroupNotificationScheduler
    list_display = ('id', 'user', 'template', 'run_at', 'repeat', 'created_at')
    search_fields = ('id', 'user', 'template')
    # change_form_template = 'admin/notification_center/group_notification_scheduler/group-notification.html'
    # form = GroupNotificationForm

    # def get_urls(self):

    #     urls = super(GroupNotificationSchedulerAdmin, self).get_urls()
    #     custom_urls = [
    #         url(
    #             r'^test',
    #             self.admin_site.admin_view(group_notification_view),
    #             name="group-notification-scheduler"
    #         ),

    #     ] + urls
    #     return custom_urls

    def save_model(self, request, obj, form, change):
        try:
            pass
            # # if first field is 
            # if obj.selection_type == "user":      
            #     user_id = obj.user.id
            #     activity_type = Template.objects.get(id=obj.template.id).type
            #     SendNotification(user_id=user_id, activity_type=activity_type).send()
            # elif obj.selection_type == "shop":
            #     pass

        except Exception as e:
            print (e.args)
            pass
        super(GroupNotificationSchedulerAdmin, self).save_model(request, obj, form, change)    

        


admin.site.register(Template, TemplateAdmin)
admin.site.register(TemplateVariable, TemplateVariableAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
#admin.site.register(TextSMSActivity, TextSMSActivityAdmin)
admin.site.register(NotificationScheduler, NotificationSchedulerAdmin)
admin.site.register(GroupNotificationScheduler, GroupNotificationSchedulerAdmin)