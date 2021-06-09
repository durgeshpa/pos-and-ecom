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
from wms.models import PosInventoryState, PosInventoryChange, PosInventory
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
    # ITEMCODE, ITEMNAME, CATEGORYNAME, MRP, CURRENTSTOCK, SellingPrice

    start_row_id = int(args[1]) if len(args) > 1 else 0
    user = User.objects.get(phone_number='7763886418')
    i_state_obj = PosInventoryState.objects.filter(inventory_state=PosInventoryState.NEW).last()
    f_state_obj = PosInventoryState.objects.filter(inventory_state=PosInventoryState.AVAILABLE).last()
    try:
        for row_id, row in enumerate(reader):
            if row_id < start_row_id:
                continue
            row = [i.strip() for i in row]

            # Look for GramFactory product
            gf_product_id = None
            gf_product = None
            sku_type = 1
            gf_products = Product.objects.filter(product_ean_code__in=[row[0], row[0].split('_')[0]],
                                                 product_mrp=round(Decimal(row[3]), 2))
            gf_products_count = gf_products.count()
            if gf_products_count >= 1:
                sku_type = 2
                gf_product = gf_products.last()
                gf_product_id = gf_product.id
            else:
                gf_products = Product.objects.filter(product_ean_code=row[0])
                gf_products_count = gf_products.count()
                if gf_products_count >= 1:
                    sku_type = 2
                    gf_product = gf_products.last()
                    gf_product_id = gf_product.id

            # remove underscore after part from ean code
            row[0] = row[0].split('_')[0]

            if RetailerProduct.objects.filter(shop_id=shop.id, name=row[1], linked_product_id=gf_product_id,
                                              mrp=round(Decimal(row[3]), 2), sku_type=sku_type,
                                              selling_price=round(Decimal(row[5]), 2),
                                              product_ean_code=row[0]).exists():
                continue
            # Create product
            product = RetailerProductCls.create_retailer_product(shop.id, row[1], round(Decimal(row[3]), 2),
                                                                 round(Decimal(row[5]), 2), gf_product_id, sku_type,
                                                                 row[1], row[0])
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
            # Add Inventory
            PosInventory.objects.create(product_id=product.id, inventory_state=f_state_obj,
                                        quantity=int(float(row[4])))
            PosInventoryCls.create_inventory_change(product.id, int(float(row[4])), PosInventoryChange.STOCK_ADD,
                                                    product.sku, i_state_obj, f_state_obj, user)
            print("Product processed {}".format(str(product)))
            print("")
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("{} {} row {}".format(exc_type, exc_tb.tb_lineno, row_id))
