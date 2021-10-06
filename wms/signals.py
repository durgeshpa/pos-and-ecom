import logging
import sys

from django.core.files.uploadedfile import InMemoryUploadedFile

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.common_utils import barcode_gen
from wms.models import ZonePutawayUserAssignmentMapping, Zone, QCArea, ZonePickerUserAssignmentMapping


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
        for user in instance.picker_users.all():
            ZonePickerUserAssignmentMapping.objects.create(zone=instance, user=user)
            info_logger.info("ZonePickerUser mapping created for zone " + str(instance) + ", user:" + str(user))
    else:
        # Putaway user mapping update
        putaway_mappings = ZonePutawayUserAssignmentMapping.objects.filter(zone=instance). \
            exclude(user__in=instance.putaway_users.all())
        if putaway_mappings:
            putaway_mappings.delete()
        for user in instance.putaway_users.all():
            ZonePutawayUserAssignmentMapping.objects.update_or_create(zone=instance, user=user, defaults={})
            info_logger.info("ZonePutawayUser mapping created for zone " + str(instance) + ", user:" + str(user))

        # Picker user mapping update
        picker_mappings = ZonePickerUserAssignmentMapping.objects.filter(zone=instance). \
            exclude(user__in=instance.picker_users.all())
        if picker_mappings:
            picker_mappings.delete()
        for user in instance.picker_users.all():
            ZonePickerUserAssignmentMapping.objects.update_or_create(zone=instance, user=user, defaults={})
            info_logger.info("ZonePickerUser mapping created for zone " + str(instance) + ", user:" + str(user))

@receiver(post_save, sender=QCArea)
def create_qc_area_barcode(sender, instance=None, created=False, update_fields=None, **kwargs):
    """ Generates barcode_txt and bar_code image for QCArea"""
    if created:
        instance.area_barcode_txt = '30' + str(instance.id).zfill(10)
        image = barcode_gen(str(instance.area_barcode_txt))
        instance.area_barcode = InMemoryUploadedFile(image, 'ImageField', "%s.jpg" % instance.area_id, 'image/jpeg',
                                                 sys.getsizeof(image), None)
        instance.save()
