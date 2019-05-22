# for doing actions based on signals
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings

from django_ses.signals import delivery_received

from django_ses.signals import bounce_received

# from notification_center.utils import GetTemplateVariables
from django.contrib.auth import get_user_model
from notification_center.utils import SendNotification



@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def user_creation_notification(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.first_name:
            username = instance.first_name
        else:
            username = instance.phone_number

        activity_type = "SIGNUP"
        data = {}
        data['username'] = username
        data['phone_number'] = instance.phone_number
        SendNotification(user_id=instance.id, activity_type=activity_type, data=data).send()    
#         message = SendSms(phone=instance.phone_number,
#                           body = '''\
#                                 Dear %s, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering.
# Thanks,
# Team GramFactory
#                                 ''' % (username))

#         message.send()

