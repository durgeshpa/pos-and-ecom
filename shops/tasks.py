# -*- coding: utf-8 -*-

from datetime import (datetime,
                      timedelta) 

from django.db.models import Q
from celery.task import task
from celery.utils.log import get_task_logger
from global_config.models import GlobalConfig
from shops.models import (Shop,
                          DayBeatPlanning)
from retailer_to_sp.models import (Order,)

logger = get_task_logger(__name__)


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
        print (cancelled_plannings)
        if cancelled_plannings:
            shops = Shop.objects.filter(
                id__in=cancelled_plannings.values_list('shop', flat=True)
            )
            print (shops, "Shop")
            cp_count = cancelled_plannings.update(is_active=False) # future daily beat plans disabled
            logger.info('task done shop {0}, plannings {1}'.format(shops, cp_count))
        else:
            logger.info('task done shop 0, plannings 0')
    else:
        logger.critical('Configure days contraint for cancelling'
                        'beat plan with KEY ::: beat_order_days :::'
                        'Example == {beat_order_day: 3}')

