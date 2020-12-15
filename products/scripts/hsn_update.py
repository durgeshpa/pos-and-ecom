import csv
import codecs
from products.models import ParentProduct, ProductHSN


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
    parent_hsn = []
    for row_id, row in enumerate(reader):
        if not row[12] == 'In-Active':
            count += 1
            try:
                ParentProduct.objects.filter(parent_id=row[1]).update(
                    product_hsn=ProductHSN.objects.filter(product_hsn_code=row[9].strip()).last())
            except:
                try:
                    hsn = "0" + row[9].strip()
                    ParentProduct.objects.filter(parent_id=row[1]).update(
                        product_hsn=ProductHSN.objects.filter(product_hsn_code=hsn).last())
                except:
                    parent_hsn.append(str(row_id+2))
        else:
            continue
    print("Total row executed :" + str(count))
    print("Product HSN is not updated in these rows :" + str(parent_hsn))
    print("Script Complete to set the product HSN from csv file")