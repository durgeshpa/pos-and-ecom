import logging

from celery.task import task
from rest_framework.authtoken.models import Token


from notification_center.utils import SendNotification
from addresses.models import Address

logger = logging.getLogger(__name__)


@task
def send_notification(*args, **kwargs):
    #setup_periodic_tasks()
    try:
        user_id = kwargs.get('user_id')
        activity_type = kwargs.get('activity_type')
        data = kwargs.get('data')
        # user_id = args[0]
        # activity_type = args[1]
        SendNotification(user_id=user_id, activity_type=activity_type, data=data).send()
    except Exception as e:
        logging.error(str(e))



@task
def schedule_notification(*args, **kwargs):
    #setup_periodic_tasks()
    try:
        # import pdb; pdb.set_trace()
        print ("in schedule_notification")
        city_id = kwargs.get('city_id')
        pincode_from = kwargs.get('pincode_from')
        pincode_to = kwargs.get('pincode_to')

        activity_type = kwargs.get('activity_type')
        
        if pincode_from:
            shop_owners = Address.objects.filter(pincode__range=(pincode_from, pincode_to)).values_list('shop_name__shop_owner')
        else:
            shop_owners = Address.objects.filter(city=city_id).values_list('shop_name__shop_owner')
        for shop_owner in shop_owners:
            user_id = shop_owner[0]
            # user_id = shop.shop_owner.id
            SendNotification(user_id=user_id, activity_type=activity_type).send()
    except Exception as e:
        logging.error(str(e))


@task
def schedule_notification_to_all(*args, **kwargs):
    #setup_periodic_tasks()
    try:
        activity_type = kwargs.get('activity_type', None)
        content = kwargs.get('content', "")
        # user_id = args[0]
        # activity_type = args[1]
        SendNotification(activity_type=activity_type).send_to_all()
    except Exception as e:
        logging.error(str(e))