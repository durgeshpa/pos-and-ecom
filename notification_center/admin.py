import json
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
            # import pdb; pdb.set_trace()
            #integrate with celery beat
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


def test_celery():
    import pdb; pdb.set_trace()
    data = {}
    #data['test'] = "test"
    data['user_id'] = 1 #user_id
    data['activity_type'] = "SIGNUP" #activity_type

    schedule= IntervalSchedule.objects.create(every=10, period=IntervalSchedule.SECONDS)
    task = PeriodicTask.objects.create(interval=schedule, name='any name2', task='tasks.schedule_notification', args=json.dumps(data))



class GroupNotificationSchedulerAdmin(admin.ModelAdmin):
    model = GroupNotificationScheduler
    list_display = ('id', 'user', 'template', 'run_at', 'repeat', 'created_at')
    search_fields = ('id', 'user', 'template')
    change_form_template = 'admin/notification_center/group_notification_scheduler/change_form.html'
    # form = GroupNotificationForm

    def save_model(self, request, obj, form, change):
        try:
            #pass
            #import pdb; pdb.set_trace()
            activity_type = Template.objects.get(id=obj.template.id).type

            if obj.selection_type == "user":      
                user_id = obj.user.id
                SendNotification(user_id=user_id, activity_type=activity_type).send()
            
            elif obj.selection_type == "shop":
                user_id = obj.shop.shop_owner.id
                SendNotification(user_id=user_id, activity_type=activity_type).send()

                related_users = obj.shop.related_users
                for user in related_users:
                    user_id = user.id
                    SendNotification(user_id=user_id, activity_type=activity_type).send()

            elif obj.selection_type == "last_order":
                shops = Shop.objects.filter(last_login_at__lte=obj.last_order)        
                for shop in shops:
                    user_id = shop.shop_owner.id
                    SendNotification(user_id=user_id, activity_type=activity_type).send()

                # fetch user id for the last order before a particular date..
                # last_order = obj.last_order
                # # fetch all users who ordered before a 
                # orders = Order.objects.filter(cart.created_at lte last_order).group_by(cart.seller_shop.shop_owner)    
                # for order in orders:
                #     user = order.cart.seller_shop.shop_owner.id
                #     SendNotification(user_id=user_id, activity_type=activity_type).send()

            elif obj.selection_type == "last_login":
                users = User.objects.filter(last_login__lte=obj.last_login)        
                for user in users:
                    user_id = user.id
                    SendNotification(user_id=user_id, activity_type=activity_type).send()

        except Exception as e:
            print (e.args)
            logging.error(str(e))
        super(GroupNotificationSchedulerAdmin, self).save_model(request, obj, form, change)    
        

admin.site.register(Template, TemplateAdmin)
admin.site.register(TemplateVariable, TemplateVariableAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
#admin.site.register(TextSMSActivity, TextSMSActivityAdmin)
admin.site.register(NotificationScheduler, NotificationSchedulerAdmin)
admin.site.register(GroupNotificationScheduler, GroupNotificationSchedulerAdmin)