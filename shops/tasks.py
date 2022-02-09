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
from shops.cron import (distance, )
from global_config.views import get_config
from retailer_to_sp.models import (Order, )

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
def set_feedbacks():
    lday = datetime.today().date() - timedelta(days=7)
    feedbacks = ExecutiveFeedback.objects.filter( latitude__isnull=False,longitude__isnull=False, feedback_date__gte=lday).order_by(
        'day_beat_plan__beat_plan__executive', 'feedback_date', 'feedback_time')
    # print(feedbacks)
    valid = []
    invalid = []
    config_distance = get_config('feedback_distance')
    for feedback in feedbacks:
        last_shop_distance = None
        feedback_lat = feedback.latitude
        feedback_lng = feedback.longitude
        shop_lat = feedback.day_beat_plan.shop.latitude
        shop_lng = feedback.day_beat_plan.shop.longitude
        if not feedback_lng or not feedback_lat or not shop_lat or not shop_lng:
            pass;
        else:
            d = distance((shop_lat, shop_lng), (feedback_lat, feedback_lng))
            d2 = round(d, 2)
            if d2 > config_distance:
                feedback.is_valid = False
                feedback.distance_in_km = d
                invalid.append([feedback.id, d2])
                feedback.save()
            elif d2 <= config_distance:
                feedback.is_valid = True
                feedback.distance_in_km = d
                valid.append([feedback.id, d2])
                feedback.save()
        if feedback_lng and feedback_lat and feedback.feedback_time:
            last_feedback_list = ExecutiveFeedback.objects.filter(
                day_beat_plan__beat_plan__executive=feedback.day_beat_plan.beat_plan.executive,
                feedback_date=feedback.feedback_date,
                feedback_time__lt=feedback.feedback_time).order_by('feedback_time')
            last_feedback = last_feedback_list.last()
            if last_feedback:
                if last_feedback.latitude and last_feedback.longitude:
                    last_shop_distance = distance((last_feedback.latitude, last_feedback.longitude),
                                                  (feedback_lat, feedback_lng))

            else:
                last_shop_distance = -0.001

            feedback.last_shop_distance = last_shop_distance
            feedback.save()
