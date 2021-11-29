import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from wkhtmltopdf.views import PDFTemplateResponse
from shops.models import DayBeatPlanning,Shop
from global_config.models import GlobalConfig
from datetime import (datetime,
                      timedelta)

def cancel_beat_plan(*args, **kwargs):
    print('Cron job to cancel daily beat planning due to order called.')
    day_config = GlobalConfig.objects.filter(key='beat_order_days').last()
    if day_config and day_config.value:
        tday = datetime.today().date()
        tday = tday - timedelta(days=1)
        print(tday, "Today")
        lday = tday - timedelta(days=int(day_config.value))
        print(lday, "Last day")
        shop = Shop.objects.filter(rt_buyer_shop_cart__rt_order_cart_mapping__created_at__gte=lday,pk=37780).last()
        print(shop.dynamic_beat)
        cancelled_plannings = DayBeatPlanning.objects.filter(
            beat_plan_date=tday,
            is_active=True,
            shop__shop_type__shop_type='r',
            shop__dynamic_beat=True,
            shop__rt_buyer_shop_cart__isnull=False,
            shop_id=37780
        )
        print (cancelled_plannings, "objects of day beat plan")
        # if cancelled_plannings:
        #     shops = Shop.objects.filter(
        #         id__in=cancelled_plannings.values_list('shop', flat=True)
        #     )
        #     print (shops, "Shop")
        #     cp_count = cancelled_plannings.update(is_active=False) # future daily beat plans disabled
        #     logger.info('task done shop {0}, plannings {1}'.format(shops, cp_count))
        # else:
        #     logger.info('task done shop 0, plannings 0')
    else:
        logger.critical('Configure days contraint for cancelling'
                        'beat plan with KEY ::: beat_order_days :::'
                        'Example == {beat_order_day: 3}')

cancel_beat_plan()