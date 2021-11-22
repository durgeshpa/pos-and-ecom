from django.core.management.base import BaseCommand
import logging

from shops.models import Shop, ShopType
info_logger = logging.getLogger('file-info')


class Command(BaseCommand):
    """
        Change Shop Type from Retailer to Franchise for existing Franchise Shops
    """
    def handle(self, *args, **options):
        shop_ids_type = {'foco': [34019,34018,34016,34000,33999,34023,34024,34021,34030,34033,34028,34025,34031,
                                  34039,34027,33997],
                         'fofo': [34426,34037,12825,4091,34015,34178,34430,30472,5403,34186,34334,23224,33797,
                                  34700,2139]}


        for shop_sub_type in shop_ids_type:
            shop_type = ShopType.objects.get(shop_type='f', shop_sub_type__retailer_type_name=shop_sub_type)

            for shop_id in shop_ids_type[shop_sub_type]:
                if Shop.objects.filter(shop_type__shop_type='r', pk=shop_id).exists():
                    shop = Shop.objects.get(pk=shop_id)
                    shop.shop_type = shop_type
                    shop.save()
                    print(shop_id)
