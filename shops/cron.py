from datetime import (datetime,
                      timedelta)
import logging
import math

from shops.models import DayBeatPlanning, ExecutiveFeedback
from global_config.views import get_config

logger = logging.getLogger('shop-cron')


def distance(shop_location, feedback_location):
    """
    Calculate distance between feedback location and shop location
    """
    lat1, lon1 = shop_location
    lat2, lon2 = feedback_location
    radius = 6371 # km

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c
    return d


def get_feedback_valid():
    """
    Function to check validity of beat planning feedback
    """
    try:
        lday = datetime.today().date() - timedelta(days=3)
        feedbacks = ExecutiveFeedback.objects.filter(latitude__isnull=False, longitude__isnull=False,
                                                     feedback_date__gte=lday).order_by(
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
                d=round(d,3)
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
                feedback.last_shop_distance = round(last_shop_distance,3)
                print(feedback)
                feedback.save()
    except Exception as error:
        logger.exception(error)
