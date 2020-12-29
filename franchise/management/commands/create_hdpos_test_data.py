from django.core.management.base import BaseCommand
import logging

import datetime
from shops.models import Shop
from franchise.models import FranchiseReturns, FranchiseSales, ShopLocationMap
from wms.models import WarehouseInventory, InventoryState, InventoryType
from products.models import Product
info_logger = logging.getLogger('file-info')


class Command(BaseCommand):
    def handle(self, *args, **options):
        shops = Shop.objects.filter(shop_type__shop_type='f')
        count = 0

        if shops.exists():
            type_normal = InventoryType.objects.filter(inventory_type='normal').last()
            state_available = InventoryState.objects.filter(inventory_state='available').last()
            for shop in shops:
                count += 1
                slm, created = ShopLocationMap.objects.get_or_create(shop=shop, location_name="Franchise_" + str(count))
                products = WarehouseInventory.objects.filter(warehouse=shop, inventory_state=state_available,
                                                  inventory_type=type_normal, in_stock=True)
                if products.exists():
                    for product in products:
                        FranchiseSales.objects.create(shop_loc=slm.location_name, barcode=product.sku.product_ean_code,
                                                      quantity=5, amount=400, invoice_date=datetime.date.today(),
                                                      invoice_number='aaaa')
                        FranchiseSales.objects.create(shop_loc=slm.location_name, barcode=product.sku.product_ean_code,
                                                      quantity=-4, amount=400, invoice_date=datetime.date.today(),
                                                      invoice_number='aaaa')
                        FranchiseSales.objects.create(shop_loc='Franchise_dummy' + str(count),
                                                      barcode=product.sku.product_ean_code,
                                                      quantity=5, amount=400, invoice_date=datetime.date.today(),
                                                      invoice_number='aaaa')
                        FranchiseReturns.objects.create(shop_loc=slm.location_name, barcode=product.sku.product_ean_code,
                                                        quantity=-2, amount=400, sr_date=datetime.date.today(),
                                                        sr_number='aaaa', invoice_number='iiii')
                        FranchiseReturns.objects.create(shop_loc=slm.location_name,
                                                        barcode=product.sku.product_ean_code,
                                                        quantity=2, amount=400, sr_date=datetime.date.today(),
                                                        sr_number='aaaa', invoice_number='iiii')
                        FranchiseReturns.objects.create(shop_loc='Franchise_dummy' + str(count),
                                                        barcode=product.sku.product_ean_code,
                                                        quantity=5, amount=400, sr_date=datetime.date.today(),
                                                        sr_number='aaaa', invoice_number='iiii')

                FranchiseSales.objects.create(shop_loc=slm.location_name, barcode='dummy',
                                              quantity=5, amount=400, invoice_date=datetime.date.today(),
                                              invoice_number='aaaa')

                FranchiseReturns.objects.create(shop_loc=slm.location_name, barcode='dummy',
                                                quantity=-5, amount=400, sr_date=datetime.date.today(),
                                                sr_number='aaaa', invoice_number='iiii')

                sample_prod = Product.objects.filter().order_by('-id')[:10]

                for sample in sample_prod:
                    FranchiseReturns.objects.create(shop_loc=slm.location_name, barcode=sample.product_ean_code,
                                                    quantity=-5, amount=400, sr_date=datetime.date.today(),
                                                    sr_number='aaaa', invoice_number='iiii')
                    FranchiseSales.objects.create(shop_loc=slm.location_name, barcode=sample.product_ean_code,
                                                  quantity=5, amount=400, invoice_date=datetime.date.today(),
                                                  invoice_number='aaaa')

        while count < 20:
            FranchiseSales.objects.create(shop_loc='Franchise_dummy' + str(count), barcode='dummy',
                                          quantity=5, amount=400, invoice_date=datetime.date.today(),
                                          invoice_number='aaaa')

            FranchiseReturns.objects.create(shop_loc='Franchise_dummy' + str(count), barcode='dummy',
                                          quantity=-5, amount=400, sr_date=datetime.date.today(),
                                          sr_number='aaaa', invoice_number='iiii')
            count += 1
