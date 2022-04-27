# -*- coding: utf-8 -*-
import logging
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from datetime import (date, datetime,
                      timedelta)

from django.db.models import Q
from celery.task import task
from celery.utils.log import get_task_logger
from global_config.models import GlobalConfig
from notification_center.fcm_notification import Device
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
    cred = credentials.Certificate()
    try:
        f_app = firebase_admin.initialize_app(cred)
    except Exception as err:
        f_app = firebase_admin.get_app()
    if not shops:
        shops = Shop.objects.filter(status=True)
    for shop in shops:
        days_limit = int(get_config('topic_order_day_limit', 90))
        start_point = datetime.today() - timedelta(days=days_limit)
        devices = list(Device.objects.filter(Q(user__rt_buyer_order__seller_shop=shop) \
            | Q(user__user_location__shop=shop), user__rt_buyer_order__created_at__gte=start_point)\
                .filter(is_active=True).distinct('reg_id').values_list('reg_id', flat=True))
        if devices:
            topic_name = f"{shop.shop_name.split(' ')[0]}_{shop.id}"
            response = messaging.subscribe_to_topic(devices, topic_name)
            cron_logger.info(f"{response.success_count} devices subscribed for shop {shop}")
            print(f"{response.success_count} devices subscribed for shop {shop}")
            cron_logger.info(f"{response.failure_count} devices not subscribed due to error for shop {shop}")
            print(f"{response.failure_count} devices not subscribed due to error for shop {shop}")
            print([f"{err.index} - {err.reason}" for err in response.errors])
            # try:
            #     shop_topic = ShopFcmTopic.objects.get(shop=shop)
            #     shop_topic.registration_ids.append(devices)
            #     shop_topic.save()
            # except ShopFcmTopic.DoesNotExist:
            #     shop_topic = ShopFcmTopic(shop=shop, topic_name=topic_name, registration_ids=devices)
            #     shop_topic.save()