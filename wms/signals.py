import logging
import sys

from django.core.files.uploadedfile import InMemoryUploadedFile

from django.db import transaction
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from accounts.models import User
from common.common_utils import barcode_gen
from retailer_to_sp.models import PickerDashboard
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


@receiver(m2m_changed, sender=Zone.putaway_users.through, dispatch_uid='putaway_users_changed', weak=False)
def putaway_users_changed(sender, instance, action, **kwargs):
    pk_set = kwargs.pop('pk_set', None)
    if action == 'post_remove':
        ZonePutawayUserAssignmentMapping.objects.filter(zone=instance, user_id__in=pk_set).delete()
    if action == 'post_add':
        for pk in pk_set:
            ZonePutawayUserAssignmentMapping.objects.update_or_create(zone=instance, user_id=pk, defaults={})
            info_logger.info("ZonePutawayUser mapping created for zone " + str(instance) + ", user id:" + str(pk))


@receiver(m2m_changed, sender=Zone.picker_users.through, dispatch_uid='picker_users_changed', weak=False)
def picker_users_changed(sender, instance, action, **kwargs):
    pk_set = kwargs.pop('pk_set', None)
    if action == 'post_remove':
        ZonePickerUserAssignmentMapping.objects.filter(zone=instance, user_id__in=pk_set).delete()
    if action == 'post_add':
        for pk in pk_set:
            ZonePickerUserAssignmentMapping.objects.update_or_create(zone=instance, user_id=pk, defaults={})
            info_logger.info("ZonePickerUser mapping created for zone " + str(instance) + ", user id:" + str(pk))


@receiver(post_save, sender=ZonePickerUserAssignmentMapping)
def reassign_picker_boy(sender, instance=None, created=False, update_fields=None, **kwargs):
    """ Reassign picker user to alternate users for the mapped orders """
    if not created and not instance.user_enabled and instance.alternate_user:
        pickers = PickerDashboard.objects.filter(picker_boy=instance.user). \
            exclude(picking_status__in=['picking_cancelled', 'moved_to_qc'])
        if pickers:
            pickers.update(picker_boy=instance.alternate_user)


@receiver(post_save, sender=QCArea)
def create_qc_area_barcode(sender, instance=None, created=False, update_fields=None, **kwargs):
    """ Generates barcode_txt and bar_code image for QCArea"""
    if created:
        instance.area_barcode_txt = '30' + str(instance.id).zfill(10)
        image = barcode_gen(str(instance.area_barcode_txt))
        instance.area_barcode = InMemoryUploadedFile(image, 'ImageField', "%s.jpg" % instance.area_id, 'image/jpeg',
                                                 sys.getsizeof(image), None)
        instance.save()
