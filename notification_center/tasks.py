import logging

from celery.task import task
from rest_framework.authtoken.models import Token


from notification_center.utils import SendNotification
from addresses.models import Address
from shops.models import ParentRetailerMapping
from shops.models import Shop

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
        import pdb; pdb.set_trace()

        print ("in schedule_notification")
        seller_shop_id = kwargs.get('seller_shop', None)
        city_id = kwargs.get('city')
        pincodes = kwargs.get('pincodes', None)
        buyer_shops = kwargs.get('buyer_shops', None)

        activity_type = kwargs.get('activity_type')
        
        # filter for location based users:
        shop_owners = None
        if buyer_shops:
            shop_owners = Address.objects.filter(shop_name__pk__in=buyer_shops).values_list('shop_name__shop_owner')
        elif pincodes:
            shop_owners = Address.objects.filter(pincode_link__pk__in=pincodes).values_list('shop_name__shop_owner')
        elif city_id:
            shop_owners = Address.objects.filter(city=city_id).values_list('shop_name__shop_owner')   
        
        # filter the users for the following sp:
        shop_owners_mapped = None
        if seller_shop_id:
            shop_owners_mapped = ParentRetailerMapping.objects.filter(parent=seller_shop_id, status=True).values_list('retailer__shop_owner')
            
        # intersection of both selections:
        shop_owners_all =  {}
        if shop_owners and shop_owners_mapped:
            shop_owners_all = set(shop_owners) & set(shop_owners_mapped)
        elif shop_owners and not shop_owners_mapped:
            shop_owners_all = shop_owners
        elif shop_owners_mapped and not shop_owners:
            shop_owners_all = shop_owners_mapped            

        for shop_owner in shop_owners_all: #(set(shop_owners) & set(shop_owners_mapped)):
            user_id = shop_owner[0]
            # user_id = shop.shop_owner.id
            # print (Shop.objects.filter(shop_owner=shop_owner[0])[0].get_shop_parent)
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