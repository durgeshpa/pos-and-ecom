from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

from shops.models import Shop

User = get_user_model()

class DateTime(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Template(models.Model):
    TEMPLATE_TYPE_CHOICES = (
        ('LOGIN', 'User logged in'),
        ('SIGNUP', 'User signed up'),
        ('PASSWORD_RESET', 'User requested password change'),
        ('SHOP_CREATED', 'User shop created'),
        ('SHOP_VERIFIED', 'User shop verified'),
        ('ORDER_CREATED', 'Order created'),
        ('ORDER_DISPATCHED', 'Order dispatched'),
        ('ORDER_SHIPPED', 'Order shipped'),
        ('ORDER_DELIVERED', 'Order delivered'),
        ('OFFER', 'Offer'),
        ('SALE', 'Sale'),
        ('SCHEME', 'Scheme'),
        ('CUSTOM', 'Custom'),
    )
    name = models.CharField(
        max_length=255
    )
    type = models.CharField(
        choices=TEMPLATE_TYPE_CHOICES,
        max_length=255,
        default='LOGIN',
        verbose_name='Type of Template',
    )
    text_email_template = models.TextField(
        verbose_name='Plain E-mail content',
        null=True, blank=True
    )
    html_email_template = models.TextField(
        verbose_name='HTML E-mail content',
        null=True, blank=True
    )
    text_sms_template = models.TextField(
        verbose_name='Text SMS content',
        null=True, blank=True
    )
    voice_call_template = models.TextField(
        verbose_name='Voice Call content',
        null=True, blank=True
    )
    gcm_title = models.CharField(
        max_length=255,
        verbose_name='Title for push notification',
        null=True, blank=True
    )
    gcm_description = models.TextField(
        max_length=255,
        verbose_name='Description for push notification',
        null=True, blank=True
    )
    gcm_image = models.ImageField(
        upload_to='gcm_banner',
        verbose_name='Banner for push notification',
        null=True, blank=True
    )
    email_alert = models.BooleanField(
        default=True,
        verbose_name='Enable/Disable email notification'
    )
    text_sms_alert = models.BooleanField(
        default=True,
        verbose_name='Enable/Disable sms notification'
    )
    voice_call_alert = models.BooleanField(
        default=True,
        verbose_name='Enable/Disable voice call notification'
    )
    gcm_alert = models.BooleanField(
        default=True,
        verbose_name='Enable/Disable mobile push notification'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return '%s-%s' % (self.name, self.get_type_display())


class TemplateVariable(models.Model):
    template = models.OneToOneField(
        Template,
        on_delete=models.CASCADE,
    )
    email_variable = models.CharField(
        max_length=255,
        verbose_name='Variable in E-mail template',
        null=True, blank=True
    )
    text_sms_variable = models.CharField(
        max_length=255,
        verbose_name='Variable in SMS template',
        null=True, blank=True
    )
    voice_call_variable = models.CharField(
        max_length=255,
        verbose_name='Variable in Voice Call template',
        null=True, blank=True
    )
    gcm_variable = models.CharField(
        max_length=255,
        verbose_name='Variable in Push Notification template',
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template']

    def __str__(self):
        return '%s' % self.template.name


class Notification(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
    )
    template = models.ForeignKey(
        Template,
        related_name='notifications',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return '%s-%s' % (self.user, self.pk)



class NotificationScheduler(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
    )
    template = models.ForeignKey(
        Template,
        related_name='notification_scheduler',
        on_delete=models.CASCADE,
    )

    run_at = models.DateTimeField(db_index=True)

    # Repeat choices are encoded as number of seconds
    # The repeat implementation is based on this encoding
    HOURLY = 3600
    DAILY = 24 * HOURLY
    WEEKLY = 7 * DAILY
    EVERY_2_WEEKS = 2 * WEEKLY
    EVERY_4_WEEKS = 4 * WEEKLY
    NEVER = 0
    REPEAT_CHOICES = (
        (HOURLY, 'hourly'),
        (DAILY, 'daily'),
        (WEEKLY, 'weekly'),
        (EVERY_2_WEEKS, 'every 2 weeks'),
        (EVERY_4_WEEKS, 'every 4 weeks'),
        (NEVER, 'never'),
    )
    repeat = models.BigIntegerField(choices=REPEAT_CHOICES, default=NEVER) #in seconds
    repeat_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return '%s-%s-%s' % (self.user, self.template, self.pk)




class GroupNotificationScheduler(models.Model):

    SELECTION_TYPE_CHOICES = (
        ('shop', 'Shop'),
        ('user', 'User'),
        ('last_login', 'Last Login'),
        ('last_order', 'Last Order'),
    )

    selection_type = models.TextField(choices=SELECTION_TYPE_CHOICES, default='user')

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
    )
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    last_login = models.DateField()
    last_order = models.DateField()

    template = models.ForeignKey(
        Template,
        related_name='group_scheduler',
        on_delete=models.CASCADE,
    )

    run_at = models.DateTimeField(db_index=True)

    # Repeat choices are encoded as number of seconds
    # The repeat implementation is based on this encoding
    HOURLY = 3600
    DAILY = 24 * HOURLY
    WEEKLY = 7 * DAILY
    EVERY_2_WEEKS = 2 * WEEKLY
    EVERY_4_WEEKS = 4 * WEEKLY
    NEVER = 0
    REPEAT_CHOICES = (
        (HOURLY, 'hourly'),
        (DAILY, 'daily'),
        (WEEKLY, 'weekly'),
        (EVERY_2_WEEKS, 'every 2 weeks'),
        (EVERY_4_WEEKS, 'every 4 weeks'),
        (NEVER, 'never'),
    )
    repeat = models.BigIntegerField(choices=REPEAT_CHOICES, default=NEVER) #in seconds
    repeat_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return '%s-%s-%s' % (self.user, self.template, self.pk)



class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email_notification = models.BooleanField(default=True)
    sms_notification = models.BooleanField(default=True)
    app_notification = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return '%s-%s' %(self.user, self.pk)


class TextSMSActivity(models.Model):
    notification = models.OneToOneField(
        Notification,
        related_name='textsmsactivities',
        on_delete=models.CASCADE,
    )
    text_sms_sent = models.BooleanField(
        default=True,
        verbose_name='Text SMS sent'
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return '%s' % self.notification

    # adding extra field to show alert status from template
    def text_sms_alert(self):
        return self.notification.template.text_sms_alert
    # for boolean into images
    text_sms_alert.boolean = True


class VoiceCallActivity(models.Model):
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
    )
    voice_call_sent = models.BooleanField(
        default=True,
        verbose_name='Voice Call sent'
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return '%s' % self.notification

    # adding extra field to show alert status from template
    def voice_call_alert(self):
        return self.notification.template.voice_call_alert
    # for boolean into images
    voice_call_alert.boolean = True


class EmailActivity(models.Model):
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
    )
    email_sent = models.BooleanField(
        default=True,
        verbose_name='E-mail sent'
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return '%s' % self.notification

    # adding extra field to show alert status from template
    def email_alert(self):
        return self.notification.template.email_alert
    # for boolean into images
    email_alert.boolean = True


class GCMActivity(models.Model):
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
    )
    gcm_sent = models.BooleanField(
        default=True,
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return '%s' % self.notification

    # adding extra field to show alert status from template
    def gcm_alert(self):
        return self.notification.template.gcm_alert
    # for boolean into images
    gcm_alert.boolean = True