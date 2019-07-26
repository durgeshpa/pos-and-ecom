import logging

from celery.task import task
from rest_framework.authtoken.models import Token

from notification_center.utils import SendNotification

logger = logging.getLogger(__name__)


@task
def schedule_notification(*args, **kwargs):
    #setup_periodic_tasks()
    try:
        user_id = kwargs.get('user_id')
        activity_type = kwargs.get('activity_type')

        # user_id = args[0]
        # activity_type = args[1]
        SendNotification(user_id=user_id, activity_type=activity_type).send()
    except Exception as e:
        logging.error(str(e))



@task
def schedule_notification_to_all(*args, **kwargs):
    #setup_periodic_tasks()
    try:
        activity_type = kwargs.get('activity_type')

        # user_id = args[0]
        # activity_type = args[1]
        SendNotification(user_id=user_id, activity_type=activity_type).send_to_all()
    except Exception as e:
        logging.error(str(e))