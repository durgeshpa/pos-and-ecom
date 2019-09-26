import json
import logging
from datetime import datetime, timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.conf.urls import url
from django_celery_beat.models import PeriodicTask, IntervalSchedule

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
from .tasks import schedule_notification


User = get_user_model()


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


class GCMActivityAdmin1(admin.ModelAdmin):
    model = GCMActivity
    fields = ['gcm_alert', 'gcm_sent', 'sent_at', 'notification']
    readonly_fields = ['gcm_sent', 'gcm_alert', 'sent_at']

    # for disabling and hiding delete button from admin
    # def has_delete_permission(self, request, obj=None):
    #     return False


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
            user_id = User.objects.get(id=obj.user.id).id
            activity_type = Template.objects.get(id=obj.template.id).type
            # code to send notification
            #setup_periodic_tasks()  #data = {}
            data = {}
            #data['test'] = "test"
            data['user_id'] = user_id
            data['activity_type'] = activity_type
            # repeat until

            schedule= IntervalSchedule.objects.create(every=obj.repeat, period=IntervalSchedule.SECONDS)
            task = PeriodicTask.objects.create(
                interval=schedule, 
                name='schedule_notification: '+str(datetime.now()), 
                task='tasks.schedule_notification',
                expires=obj.repeat_until, 
                args=json.dumps(['66']),
                kwargs=json.dumps(data))

            #setup_periodic_tasks()
            #SendNotification(user_id=user_id, activity_type=activity_type).send()
        except Exception as e:
            print (e.args)
            pass
        super(NotificationSchedulerAdmin, self).save_model(request, obj, form, change)    


class GroupNotificationSchedulerAdmin(admin.ModelAdmin):
    model = GroupNotificationScheduler
    #raw_id_fields = ('buyer_shop')
    list_display = ('id', 'template', 'run_at', 'repeat', 'created_at')
    search_fields = ('id', 'template')
    #change_form_template = 'admin/notification_center/group_notification_scheduler/change_form.html'
    form = GroupNotificationForm

    def save_model(self, request, obj, form, change):
        #import pdb; pdb.set_trace()
        try:
            data = {}
            #data['test'] = "test"
            city = form.cleaned_data.get('city', None)
            pincode_from = form.cleaned_data.get('pincode_from', None)
            pincode_to = form.cleaned_data.get('pincode_to', None)
            buyer_shop = form.cleaned_data.get('buyer_shop', None)

            if city:
                data['city'] = form.cleaned_data.get('city').id
            if pincode_from:
                data['pincode_from'] = form.cleaned_data.get('pincode_from').pincode
            if pincode_to:
                data['pincode_to'] = form.cleaned_data.get('pincode_to').pincode
            # if buyer_shop:
            #     data['buyer_shop'] = form.cleaned_data.get('buyer_shop').id
            data['activity_type'] = obj.template.id#.type
            # repeat until

            schedule_notification(**data)

            # schedule= IntervalSchedule.objects.create(every=obj.repeat, period=IntervalSchedule.SECONDS)

            # task = PeriodicTask.objects.create(
            #     interval=schedule, 
            #     name='schedule_notification: '+str(datetime.now()), 
            #     task='tasks.schedule_notification',
            #     expires=obj.repeat_until, 
            #     start_time=obj.run_at,
            #     #args=json.dumps(['66']),
            #     kwargs=json.dumps(data))
        except Exception as e:
            print (e)
        super(GroupNotificationSchedulerAdmin, self).save_model(request, obj, form, change)    
        

admin.site.register(Template, TemplateAdmin)
admin.site.register(TemplateVariable, TemplateVariableAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
#admin.site.register(TextSMSActivity, TextSMSActivityAdmin)
admin.site.register(NotificationScheduler, NotificationSchedulerAdmin)
admin.site.register(GroupNotificationScheduler, GroupNotificationSchedulerAdmin)
admin.site.register(GCMActivity, GCMActivityAdmin1)
