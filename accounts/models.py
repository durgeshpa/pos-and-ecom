from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.core.validators import RegexValidator
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from otp.sms import SendSms
import datetime
from .tasks import phone_otp_instance
from django.db import transaction
from rest_framework.authtoken.models import Token


USER_TYPE_CHOICES = (
        (1, 'Administrator'),
        (2, 'Distributor Executive'),
        (3, 'Distributor Manager'),
        (4, 'Operation Executive'),
        (5, 'Operation Manager'),
        (6, 'Sales Executive'),
        (7, 'Sales Manager'),
    )

USER_DOCUMENTS_TYPE_CHOICES = (
    ("pc", "PAN Card"),
    ("dl", "Driving License"),
    ("uidai", "Aadhaar Card"),
)

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, phone_number, password, **extra_fields):
        """Create and save a User with the given phone and password."""
        if not phone_number:
            raise ValueError('The given phone must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        """Create and save a regular User with the given phone and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password, **extra_fields):
        """Create and save a SuperUser with the given phone and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(phone_number, password, **extra_fields)

class User(AbstractUser):
    """User model."""
    username = None
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False, unique=True)
    email = models.EmailField(_('email address'),blank=True)
    user_photo = models.ImageField(upload_to='user_photos/', null=True, blank=True)
    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default = '6', null=True)
    imei_no = models.CharField(max_length=20,null=True,blank=True)

    USERNAME_FIELD = 'phone_number'
    objects = UserManager()

    def user_photo_thumbnail(self):
        return mark_safe('<img alt="%s" src="%s" />' % (self.user, self.user_photo.url))

    def __str__(self):
        return "%s"%(str(self.phone_number))


class UserWithName(User):
    class Meta:
        proxy = True

    def __str__(self):
        if self.first_name and self.last_name:
            return "%s - %s %s" % (
                str(self.phone_number), self.first_name, self.last_name
            )

        elif self.first_name:
            return "%s - %s" % (str(self.phone_number), self.first_name)

        return "%s" % (str(self.phone_number))


class UserDocument(models.Model):
    user = models.ForeignKey(User, related_name='user_documents', on_delete=models.CASCADE)
    user_document_type = models.CharField(max_length=100, choices=USER_DOCUMENTS_TYPE_CHOICES, default='uidai')
    user_document_number = models.CharField(max_length=100)
    user_document_photo = models.FileField(upload_to='user_photos/documents/')

    def user_document_photo_thumbnail(self):
        return mark_safe('<img alt="%s" src="%s" />' % (self.user, self.user_document_photo.url))

    def __str__(self):
        return "%s - %s"%(self.user, self.user_document_number)

    class Meta:
        verbose_name = "User Document"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def user_creation_notification(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.first_name:
            username = instance.first_name
        else:
            username = instance.phone_number
        message = SendSms(phone=instance.phone_number,
                          body = '''\
                                Dear %s, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering.
Thanks,
Team GramFactory
                                ''' % (username))

        message.send()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_phone_otp_instance(sender, instance=None, created=False, **kwargs):
    if created:
        transaction.on_commit(
            lambda: phone_otp_instance.delay(instance.phone_number, created))


class AppVersion(models.Model):
    app_version = models.CharField(max_length=200)
    update_recommended = models.BooleanField(default=False)
    force_update_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.app_version