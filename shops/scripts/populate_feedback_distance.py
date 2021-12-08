# python imports
import logging
import traceback

# app imports
from shops.models import ExecutiveFeedback
from shops.cron import distance

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run():
    set_feedback_distance()


def set_feedback_distance():
    try:
        info_logger.info('Set feedback distance when distance is null|started')
        print(1)
        executive_feedback = ExecutiveFeedback.objects.filter(distance_in_km__isnull = True)  # distance=NULL
        print(executive_feedback)
        if executive_feedback:
            for feedback in executive_feedback:
                feedback_lat = feedback.latitude
                feedback_lng = feedback.longitude
                shop_lat = feedback.day_beat_plan.shop.latitude
                shop_lng = feedback.day_beat_plan.shop.longitude
                print(feedback_lat, feedback_lng, shop_lat, shop_lng)
                if not feedback_lng or not feedback_lat or not shop_lat or not shop_lng:
                    continue
                d = distance((shop_lat, shop_lng), (feedback_lat, feedback_lng))
                feedback.update(distance_in_km = d)
                print("feedback updated {} distance {}".format(feedback.id, feedback.distance))
    except Exception as e:
        traceback.print_exc()
