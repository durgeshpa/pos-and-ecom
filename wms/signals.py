import logging
import sys

from django.core.files.uploadedfile import InMemoryUploadedFile

from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save, m2m_changed, pre_save
from django.dispatch import receiver

from accounts.models import User
from common.common_utils import barcode_gen
from retailer_to_sp.models import PickerDashboard, ShopCrate
from wms.models import ZonePutawayUserAssignmentMapping, Zone, QCArea, ZonePickerUserAssignmentMapping, Crate, QCDesk, \
    QCDeskQCAreaAssignmentMapping, QCDeskQCAreaAssignmentMappingTransactionLog
from wms.views import auto_qc_area_assignment_to_order

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


@receiver(post_save, sender=QCDesk)
def create_qc_desk_number(sender, instance=None, created=False, update_fields=None, **kwargs):
    """
        QCDesk number on creation / updation
    """
    if not instance.desk_number:
        desk_count = QCDesk.objects.filter(warehouse=instance.warehouse, desk_number__isnull=False).count()
        instance.desk_number = "W" + str(instance.warehouse.id).zfill(6) + "D" + str(desk_count + 1).zfill(2)
        instance.save()
    if instance and not instance.desk_enabled and instance.alternate_desk:
        instance.alternate_desk.qc_areas.add(*list(instance.qc_areas.values_list('pk', flat=True)))
    if instance and instance.desk_enabled:
        area_in_another_desk = QCDesk.objects.filter(
            qc_areas__in=instance.qc_areas.all()).exclude(pk=instance.pk).distinct()
        for desk in area_in_another_desk:
            desk.qc_areas.remove(*list(instance.qc_areas.values_list('pk', flat=True)))


@receiver(m2m_changed, sender=QCDesk.qc_areas.through, dispatch_uid='qc_areas_changed', weak=False)
def qc_areas_changed(sender, instance, action, **kwargs):
    pk_set = kwargs.pop('pk_set', None)
    if action == 'post_remove':
        QCDeskQCAreaAssignmentMapping.objects.filter(qc_desk=instance, qc_area_id__in=pk_set).delete()
    if action == 'post_add':
        for pk in pk_set:
            QCDeskQCAreaAssignmentMapping.objects.update_or_create(
                qc_desk=instance, qc_area_id=pk,
                defaults={"created_by": instance.updated_by, "updated_by": instance.updated_by})
            info_logger.info("QC Desk to QC Area mapping created for qc_desk " + str(instance) + ", area id:" + str(pk))


@receiver(pre_save, sender=QCDeskQCAreaAssignmentMapping)
def create_logs_for_qc_desk_area_mapping(sender, instance=None, created=False, **kwargs):
    if not instance._state.adding:
        try:
            old_ins = QCDeskQCAreaAssignmentMapping.objects.get(id=instance.id)
            QCDeskQCAreaAssignmentMappingTransactionLog.objects.create(
                qc_desk=old_ins.qc_desk, qc_area=old_ins.qc_area, token_id=old_ins.token_id, qc_done=old_ins.qc_done,
                created_by=old_ins.updated_by, updated_by=old_ins.updated_by)
        except:
            pass


@receiver(post_save, sender=QCDeskQCAreaAssignmentMapping)
def assign_token_for_existing_qc_area(sender, instance=None, created=False, update_fields=None, **kwargs):
    """ Assign Token for exiting QC Area mapped order """
    if instance.token_id is None and instance.qc_area:
        picker_instance = PickerDashboard.objects.filter(qc_area=instance.qc_area). \
            filter(Q(order__rt_order_order_product__isnull=True) |
                   Q(order__rt_order_order_product__shipment_status='SHIPMENT_CREATED')). \
            filter(picking_status__in=[PickerDashboard.PICKING_COMPLETE, PickerDashboard.MOVED_TO_QC]).last()
        if picker_instance and picker_instance.order:
            instance.token_id = picker_instance.order.order_no
            instance.qc_done = False
            instance.save()

    # Trigger to auto assign QC Area
    if instance.qc_done:
        auto_qc_area_assignment_to_order()


@receiver(post_save, sender=ZonePickerUserAssignmentMapping)
def reassign_picker_boy(sender, instance=None, created=False, update_fields=None, **kwargs):
    """ Reassign picker user to alternate users for the mapped orders """
    if not created and not instance.user_enabled and instance.alternate_user:
        pickers = PickerDashboard.objects.filter(picker_boy=instance.user). \
            exclude(picking_status__in=['picking_cancelled', 'moved_to_qc'])
        if pickers:
            pickers.update(picker_boy=instance.alternate_user)


@receiver(post_save, sender=PickerDashboard)
def assign_clickable_state(sender, instance=None, created=False, update_fields=None, **kwargs):
    if created:
        picker = PickerDashboard.objects.filter(picker_boy_id=instance.user, picking_status='picking_assigned').order_by(
            'picker_assigned_date').first()
        picker.is_clickable = True
        picker.save()


@receiver(post_save, sender=QCArea)
def create_qc_area_barcode(sender, instance=None, created=False, update_fields=None, **kwargs):
    """ Generates barcode_txt and bar_code image for QCArea"""
    if created:
        instance.area_barcode_txt = '30' + str(instance.id).zfill(10)
        image = barcode_gen(str(instance.area_barcode_txt))
        instance.area_barcode = InMemoryUploadedFile(image, 'ImageField', "%s.jpg" % instance.area_id, 'image/jpeg',
                                                 sys.getsizeof(image), None)
        instance.save()


@receiver(post_save, sender=Crate)
def create_crate_barcode(sender, instance=None, created=False, update_fields=None, **kwargs):
    """ Generates barcode_txt and bar_code image for QCArea"""
    if created:
        instance.crate_barcode_txt = '04' + str(instance.id).zfill(10)
        image = barcode_gen(str(instance.crate_barcode_txt))
        instance.crate_barcode = InMemoryUploadedFile(image, 'ImageField', "%s.jpg" % instance.crate_id, 'image/jpeg',
                                                 sys.getsizeof(image), None)
        instance.save()
        info_logger.info(f"create_crate_barcode|Barcode created|Crate {instance}")
        shop_crate_instance, _ = ShopCrate.objects.update_or_create(shop=instance.warehouse, crate=instance,
                                                                    defaults={'is_available': True})
        info_logger.info(f"create_crate_barcode|ShopCrate|shop_id {instance.warehouse.id} | crate_db_id {instance.id} "
                         f"Crate Id {shop_crate_instance.crate.crate_id}| is_available True")
