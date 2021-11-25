import datetime
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
        previous_date = datetime.date.today() - datetime.timedelta(days=1)
        beat_plan = DayBeatPlanning.objects.filter(next_plan_date__gte=previous_date)
        executive_feedback = ExecutiveFeedback.objects.filter(day_beat_plan__in=beat_plan)
        print(executive_feedback)
        for feedback in executive_feedback:
            feedback_lat = feedback.latitude
            feedback_lng = feedback.longitude
            shop_lat = feedback.day_beat_plan.shop.latitude
            shop_lng = feedback.day_beat_plan.shop.longitude
            print(feedback_lat, feedback_lng, shop_lng, shop_lat)
            if not feedback_lng or not feedback_lat or not shop_lat or not shop_lng:
                continue
            else:
                d = distance((shop_lat, shop_lng), (feedback_lat, feedback_lng))
                config_distance = get_config('feedback_distance')
                if d > config_distance:
                    feedback.is_valid = False
                    feedback.save()
                elif d <= config_distance:
                    feedback.is_valid = True
                    feedback.save()
                print(feedback.is_valid)
    except Exception as error:
        logger.exception(error)
