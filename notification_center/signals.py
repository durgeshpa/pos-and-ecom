# for doing actions based on signals
from django.dispatch import receiver
from django.db.models.signals import post_save

from django_ses.signals import delivery_received

from django_ses.signals import bounce_received

# from notification_center.utils import GetTemplateVariables
from notification_center.models import Template

from fcm.utils import get_device_model
from shops.tasks import unsubscribe_inactive_token


# @receiver(post_save, sender=Template)
# def create_template_variables(sender, instance=None, created=False, **kwargs):
#     template_variable = GetTemplateVariables(instance)
#     template_variable.create()
#     from django.core.mail import send_mail, EmailMessage

#     send_mail(
#         'Subject here',
#         'Here is the message.',
#         'dev@gramfactory.com',
#         ['jagjeet@gramfactory.com'],
#         fail_silently=False,
#     )


@receiver(delivery_received)
def delivery_handler(sender, *args, **kwargs):
    print("This is delivery email object")
    print(kwargs.get('mail_obj'))


@receiver(bounce_received)
def bounce_handler(sender, *args, **kwargs):
    print("This is bounce email object")
    print(kwargs.get('mail_obj'))


@receiver(post_save, sender=get_device_model())
def post_save_device_model(sender, instance, created=False, **kwargs):
    if instance.is_active == False:
        unsubscribe_inactive_token(instance.reg_id)