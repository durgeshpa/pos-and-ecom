# -*- coding: utf-8 -*-
import re
import logging
import firebase_admin
from firebase_admin import messaging
from datetime import (date, datetime,
                      timedelta)

from django.db.models import Q
from celery.task import task
from celery.utils.log import get_task_logger
from global_config.models import GlobalConfig
from shops.models import (Shop,
                          DayBeatPlanning,
                          ExecutiveFeedback, ShopFcmTopic)
from shops.cron import (distance, )
from global_config.views import get_config
from retailer_to_sp.models import (Order, )
from fcm.utils import get_device_model
from ecom.models import ShopUserLocationMappedLog
from django.db.models import Subquery

Device = get_device_model()

logger = get_task_logger(__name__)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')



@task
def cancel_beat_plan(*args, **kwargs):
    logger.info('Cron job to cancel daily beat planning due to order called.')
    day_config = GlobalConfig.objects.filter(key='beat_order_days').last()
    if day_config and day_config.value:
        tday = datetime.today().date()
        lday = tday - timedelta(days=int(day_config.value))
        cancelled_plannings = DayBeatPlanning.objects.filter(
            # Q(
            #     Q(beat_plan_date=tday) |
            #     Q(next_plan_date__gt=tday)
            # ),
            beat_plan_date=tday,
            is_active=True,
            shop__shop_type__shop_type='r',
            shop__dynamic_beat=True,
            shop__rt_buyer_shop_cart__isnull=False,
            shop__rt_buyer_shop_cart__rt_order_cart_mapping__created_at__gte=lday
        )
        if cancelled_plannings:
            shops = Shop.objects.filter(
                id__in=cancelled_plannings.values_list('shop', flat=True)
            )
            cp_count = cancelled_plannings.update(is_active=False)  # future daily beat plans disabled
            logger.info('task done shop {0}, plannings {1}'.format(shops, cp_count))
        else:
            logger.info('task done shop 0, plannings 0')
    else:
        logger.critical('Configure days contraint for cancelling'
                        'beat plan with KEY ::: beat_order_days :::'
                        'Example == {beat_order_day: 3}')


@task
def create_topics_on_fcm(shops=None):
    try:
        f_app = firebase_admin.initialize_app()
    except Exception as err:
        f_app = firebase_admin.get_app()
    if not shops:
        shops = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, pos_enabled=True)
    for shop in shops:
        days_limit = int(get_config('topic_order_day_limit', 90))
        start_point = datetime.today() - timedelta(days=days_limit)
        devices = list(Device.objects.filter(Q(user__rt_buyer_order__seller_shop=shop) \
            | Q(user__user_location__shop=shop), user__rt_buyer_order__created_at__gte=start_point)\
                .filter(is_active=True).distinct('reg_id').values_list('reg_id', flat=True))
        old_devices = shop.fcm_topics.values_list('registration_ids', flat=True)
        if old_devices:
            devices = [device for device in devices if device not in old_devices[0]]
        if devices:
            shop_name = re.sub('\W+','', shop.shop_name.split(' ')[0])
            topic_name = f"{shop_name}_{shop.id}"
            response = messaging.subscribe_to_topic(devices, topic_name)
            cron_logger.info(f"{response.success_count} devices subscribed for shop {shop}")
            cron_logger.info(f"{response.failure_count} devices not subscribed due to error for shop {shop}")
            print(f"{response.success_count} devices subscribed for shop {shop}")
            print(f"{response.failure_count} devices not subscribed due to error for shop {shop}")
            print([f"{err.index} - {err.reason}" for err in response.errors])
            try:
                shop_topic = ShopFcmTopic.objects.get(shop=shop)
                shop_topic.registration_ids.extend(devices)
                shop_topic.save()
            except ShopFcmTopic.DoesNotExist:
                shop_topic = ShopFcmTopic(shop=shop, topic_name=topic_name, registration_ids=devices)
                shop_topic.save()
    firebase_admin.delete_app(f_app)


@task
def remove_stale_users():
    try:
        f_app = firebase_admin.initialize_app()
    except Exception as err:
        f_app = firebase_admin.get_app()
    shops = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, pos_enabled=True)
    for shop in shops:
        stale_limit = int(get_config('topic_order_day_limit', 90))
        dead_point = datetime.today() - timedelta(days=stale_limit)
        days_limit = int(get_config('topic_order_day_limit', 90))
        start_point = datetime.today() - timedelta(days=days_limit)
        old_devices = Device.objects.filter(user__rt_buyer_order__seller_shop=shop,
                                            user__rt_buyer_order__created_at__lte=dead_point)
        unsubscribed_devices = list(
            Device.objects.filter(id__in=Subquery(old_devices.values('id')))\
                .exclude(user__rt_buyer_order__seller_shop=shop,
                        user__rt_buyer_order__created_at__gte=start_point)\
                            .filter(is_active=True).distinct('reg_id').values_list('reg_id', flat=True)
        )
        cron_logger.info(f"{len(unsubscribed_devices)} devices unsubscribed for shop {shop}")
        if unsubscribed_devices:
            shop_name = re.sub('\W+','', shop.shop_name.split(' ')[0])
            topic_name = f"{shop_name}_{shop.id}"
            response = messaging.unsubscribe_from_topic(unsubscribed_devices, topic_name)
            cron_logger.info(f"{response.success_count} devices unsubscribed for shop {shop}")
            cron_logger.info(f"{response.failure_count} devices not unsubscribed due to error for shop {shop}")
            print(f"{response.failure_count} devices not unsubscribed due to error for shop {shop}")
            print([f"{err.index} - {err.reason}" for err in response.errors])
            print(f"{response.success_count} devices unsubscribed for shop {shop}")
            try:
                shop_topic = ShopFcmTopic.objects.get(shop=shop)
                left_devices = [device for device in shop_topic.registration_ids if device not in unsubscribed_devices]
                shop_topic.registration_ids = left_devices
                shop_topic.save()
            except ShopFcmTopic.DoesNotExist:
                pass
    firebase_admin.delete_app(f_app)


@task
def replace_device_token(old, new):
    topics = ShopFcmTopic.objects.filter(registration_ids__contains=[old])
    try:
        f_app = firebase_admin.initialize_app()
    except Exception as err:
        f_app = firebase_admin.get_app()
    for topic in topics:
        topic_name = topic.topic_name
        unsub_response = messaging.unsubscribe_from_topic([old], topic_name)
        topic.registration_ids.pop(old)
        cron_logger.info(f"{unsub_response.success_count} devices unsubscribed for topic {topic}")
        cron_logger.info(f"{unsub_response.failure_count} devices not unsubscribed due to error for topic {topic}")
        sub_response = messaging.subscribe_to_topic([new], topic_name)
        topic.registration_ids.append(new)
        cron_logger.info(f"{sub_response.success_count} devices subscribed for topic {topic}")
        cron_logger.info(f"{sub_response.failure_count} devices not subscribed due to error for topic {topic}")
    firebase_admin.delete_app(f_app)


@task
def unsubscribe_inactive_token(token):
    topics = ShopFcmTopic.objects.filter(registration_ids__contains=[token])
    try:
        f_app = firebase_admin.initialize_app()
    except Exception as err:
        f_app = firebase_admin.get_app()
    for topic in topics:
        topic_name = topic.topic_name
        unsub_response = messaging.unsubscribe_from_topic([token], topic_name)
        topic.registration_ids.pop(token)
        topic.save()
        cron_logger.info(f"{unsub_response.success_count} devices unsubscribed for topic {topic}")
        cron_logger.info(f"{unsub_response.failure_count} devices not unsubscribed due to error for topic {topic}")
    firebase_admin.delete_app(f_app)