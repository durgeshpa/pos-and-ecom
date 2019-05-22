import logging

from celery.task import task
from rest_framework.authtoken.models import Token

from notification_center.utils import SendNotification

logger = logging.getLogger(__name__)


@task
def schedule_notification_task(*args):
    #setup_periodic_tasks()
    try:
    	user_id = args[0]
    	activity_type = args[1]
	    SendNotification(user_id=user_id, activity_type=activity_type).send()
	except Exception as e:
		logging.error(str(e))
