import csv
import codecs
from decimal import Decimal
import sys
import requests
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile

from shops.models import Shop
from products.models import Product
from pos.common_functions import RetailerProductCls, PosInventoryCls
from wms.models import PosInventoryState, PosInventoryChange
from accounts.models import User
from pos.models import RetailerProduct
from pos.api.v1.serializers import ImageFileSerializer


def run(*args):
    print("Started")
    print("")

    if not args:
        print("Please provide shop id as argument")
        return

    try:
        shop = Shop.objects.get(id=args[0])
        print(shop.shop_name)
        print("")
    except:
        print('Shop not found')
        return

    f = open('pos/scripts/pos_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    titles = next(reader)
    # ITEMCODE, ITEMNAME, CATEGORYNAME, MRP, CURRENTSTOCK, SellingPrice

    try:
        created_count = 0
        updated_count = 0
        user = User.objects.get(phone_number='7763886418')
        for row_id, row in enumerate(reader):
            # Remove end spaces
            row = [i.strip() for i in row]

            # Look for GramFactory product to link
            gf_product_id = None
            gf_product = None
            sku_type = 1
            gf_products = Product.objects.filter(product_ean_code=row[0])
            gf_products_count = gf_products.count()
            if gf_products_count >= 1:
                gf_products_n = Product.objects.filter(product_ean_code=row[0], product_mrp=round(Decimal(row[3]), 2))
                gf_products_count = gf_products_n.count()
                if gf_products_count >= 1:
                    sku_type = 2
                    gf_product = gf_products_n.last()
                    gf_product_id = gf_product.id
                else:
                    sku_type = 2
                    gf_product = gf_products.last()
                    gf_product_id = gf_product.id
            else:
                eans = [row[0].split('_')[0], row[0].split('_')[0] + '_' + str(int(Decimal(row[3])))]
                gf_products = Product.objects.filter(product_ean_code__in=eans,
                                                     product_mrp=round(Decimal(row[3]), 2))
                gf_products_count = gf_products.count()
                if gf_products_count >= 1:
                    sku_type = 2
                    gf_product = gf_products.last()
                    gf_product_id = gf_product.id

            # Remove underscore and part after that - from ean code
            row[0] = row[0].split('_')[0]

            # Update product and inventory
            if RetailerProduct.objects.filter(shop_id=shop.id, mrp=round(Decimal(row[3]), 2),
                                              name=row[1],
                                              product_ean_code=row[0]).exists():
                product = RetailerProduct.objects.get(shop_id=shop.id, mrp=round(Decimal(row[3]), 2),
                                                      name=row[1],
                                                      product_ean_code=row[0])
                product.selling_price = round(Decimal(row[5]), 2)
                product.description = row[1]
                product.name = row[1]
                product.save()

                PosInventoryCls.stock_inventory(product.id, PosInventoryState.AVAILABLE, PosInventoryState.AVAILABLE,
                                                int(float(row[4])), user, product.sku, PosInventoryChange.STOCK_UPDATE)
                print("Product updated {}".format(str(product)))
                print("")
                updated_count += 1
                continue

            # Create product, inventory, images
            product = RetailerProductCls.create_retailer_product(shop.id, row[1], round(Decimal(row[3]), 2),
                                                                 round(Decimal(row[5]), 2), gf_product_id, sku_type,
                                                                 row[1], row[0])
            # Upload GF linked product available images
            if gf_product:
                images = []
                image_objs = gf_product.product_pro_image.all()
                if image_objs:
                    for image_obj in image_objs:
                        try:
                            response = requests.get(image_obj.image.url)
                            image = BytesIO(response.content)
                            image = InMemoryUploadedFile(image, 'ImageField', "gmfact_image.jpeg", 'image/jpeg',
                                                         sys.getsizeof(image),
                                                         None)
                            serializer = ImageFileSerializer(data={'image': image})
                            if serializer.is_valid():
                                images += [image]
                        except:
                            pass
                    RetailerProductCls.create_images(product, images)
                    product.save()
            PosInventoryCls.stock_inventory(product.id, PosInventoryState.NEW, PosInventoryState.AVAILABLE,
                                            int(float(row[4])), user, product.sku, PosInventoryChange.STOCK_ADD)

            print("Product created {}".format(str(product)))
            print("")
            created_count += 1
        print("Products created {}".format(created_count))
        print("Products updated {}".format(updated_count))
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("{} {} row {}".format(exc_type, exc_tb.tb_lineno, row_id + 1))
