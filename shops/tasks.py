# -*- coding: utf-8 -*-

from datetime import (datetime,
                      timedelta) 

from django.db.models import Q
from celery.task import task
from celery.utils.log import get_task_logger
from global_config.models import GlobalConfig
from shops.models import (Shop,
                          DayBeatPlanning, 
                          ExecutiveFeedback)
from shops.cron import (distance,)
from global_config.views import get_config
from retailer_to_sp.models import (Order,)

logger = get_task_logger(__name__)


@task
def cancel_beat_plan(*args, **kwargs):
    logger.info('Cron job to cancel daily beat planning due to order called.')
    day_config = GlobalConfig.objects.filter(key='beat_order_days').last()
    if day_config and day_config.value:
        tday = datetime.today().date()
        print(tday, "Today")
        lday = tday - timedelta(days=int(day_config.value))
        print(lday, "Last day")
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
        print (cancelled_plannings, "objects of day beat plan")
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

@task
def set_feedbacks():
    feedbacks = ExecutiveFeedback.objects.filter(day_beat_plan__shop__latitude__isnull=False, 
                                                 day_beat_plan__shop__longitude__isnull=False, 
                                                 latitude__isnull=False, 
                                                 longitude__isnull=False)
    print(len(feedbacks))
    valid = []
    invalid = []
    for feedback in feedbacks:
        feedback_lat = feedback.latitude
        feedback_lng = feedback.longitude
        shop_lat = feedback.day_beat_plan.shop.latitude
        shop_lng = feedback.day_beat_plan.shop.longitude
        # print(feedback_lat, feedback_lng, shop_lat, shop_lng)
        if not feedback_lng or not feedback_lat or not shop_lat or not shop_lng:
            continue
        else:
            d = distance((shop_lat, shop_lng), (feedback_lat, feedback_lng))
            # print(d)
            config_distance = get_config('feedback_distance')
            if d > config_distance:
                feedback.is_valid = False
                feedback.distance_in_km = d
                valid.append(feedback.id)
                feedback.save()
            elif d <= config_distance:
                feedback.is_valid = True
                feedback.distance_in_km = d
                invalid.append(feedback.id)
                feedback.save()
    print("Valid feedbacks", valid)
    print("Invalid feedbacks", invalid)