from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile, MLMUser


@receiver(post_save, sender=MLMUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=MLMUser)
def save_profile(sender, instance, **kwargs):
    print("save")
    instance.profile.save()
