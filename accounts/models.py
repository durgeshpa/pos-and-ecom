from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from rest_framework.authtoken.models import Token
from django.core.validators import RegexValidator
from django.utils.crypto import get_random_string


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

    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="The phone number entered is not valid")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False, unique=True)
    email = models.EmailField(_('email address'),blank=True)
    USER_TYPE_CHOICES = (
        (1, 'Administrator'),
        (2, 'Distributor Executive'),
        (3, 'Distributor Manager'),
        (4, 'Operation Executive'),
        (5, 'Operation Manager'),
        (6, 'Sales Executive'),
        (7, 'Sales Manager'),
    )

    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default = '6', null=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']
    objects = UserManager()

    def __str__(self):
        return str(self.phone_number)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
from otp.models import PhoneOTP
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_phone_otp(sender, instance=None, created=False, **kwargs):
    if created:
        PhoneOTP.create_otp_for_number(instance)
