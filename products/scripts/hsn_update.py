import logging
import csv
import codecs
from products.models import ParentProduct, ProductHSN

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run():
    set_product_hsn()


def set_product_hsn():
    """
    This method is used for set the HSN
    """
    f = open('products/scripts/hsn_update.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8'))
    first_row = next(reader)
    print("Script Start to set the product HSN from csv file")
    count = 0
    for row_id, row in enumerate(reader):
        count += 1
        try:
            print("Total row executed :" + str(count))
            product_hsn_object = ProductHSN.objects.filter(product_hsn_code=row[5].strip())
            if product_hsn_object:
                ParentProduct.objects.filter(parent_id=row[0]).update(
                    product_hsn=ProductHSN.objects.filter(product_hsn_code=product_hsn_object.last()).last())
            else:
                product_hsn_object, created = ProductHSN.objects.get_or_create(product_hsn_code=row[5].strip())
                if created:
                    ParentProduct.objects.filter(parent_id=row[0]).update(
                        product_hsn=ProductHSN.objects.filter(product_hsn_code=product_hsn_object).last())

        except Exception as e:
            error_logger.error(e)

    print("Script Complete to set the product HSN from csv file")