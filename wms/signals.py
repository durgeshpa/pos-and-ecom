import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from wms.models import ZonePutawayUserAssignmentMapping, Zone

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


@receiver(post_save, sender=Zone)
def create_zone_putaway_user_assignment_mapping(sender, instance=None, created=False, update_fields=None, **kwargs):
    """
        ZonePutawayUserAssignmentMapping on Zone creation / updation
    """
    if not instance.zone_number:
        zone_count = Zone.objects.filter(warehouse=instance.warehouse).count()
        instance.zone_number = "W" + str(instance.warehouse.id).zfill(6) + "Z" + str(zone_count + 1).zfill(2)
        instance.save()
    if created:
        for user in instance.putaway_users.all():
            ZonePutawayUserAssignmentMapping.objects.create(zone=instance, user=user)
            info_logger.info("ZonePutawayUser mapping created for zone " + str(instance) + ", user:" + str(user))
    else:
        mappings = ZonePutawayUserAssignmentMapping.objects.filter(zone=instance). \
            exclude(user__in=instance.putaway_users.all())
        if mappings:
            mappings.delete()
        for user in instance.putaway_users.all():
            ZonePutawayUserAssignmentMapping.objects.update_or_create(zone=instance, user=user, defaults={})
            info_logger.info("ZonePutawayUser mapping created for zone " + str(instance) + ", user:" + str(user))
