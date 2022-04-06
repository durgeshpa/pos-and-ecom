import logging
from django.db.models import Count
from shops.models import DayBeatPlanning

script_logger = logging.getLogger('cron_log')

def run():
    remove_duplicate_feedbacks()


def remove_duplicate_feedbacks():
    objs = DayBeatPlanning.objects.annotate(feed_count=Count('day_beat_plan')).filter(feed_count__gt=1)
    #print("Duplicates found", objs.count())
    script_logger.info('Start :: Duplicate Feedback found {}'.format(objs.count()))
    for obj in objs:
        script_logger.info('Feedback deleted for daily beat plan {} and feedback | duplicate {} | non duplicate {}'.format(obj.id, 
                                                                                                                         obj.day_beat_plan.first().id,
                                                                                                                         obj.day_beat_plan.last().id))
        # print('Feedback deleted for daily beat plan {} and feedback | duplicate {} | non duplicate {}'.format(obj.id, 
        #                                                                                                     obj.day_beat_plan.first().id,
        #                                                                                                     obj.day_beat_plan.last().id))
        obj.day_beat_plan.first().delete()
    script_logger.info('Finished :: Duplicate Feedbacks removed')
        