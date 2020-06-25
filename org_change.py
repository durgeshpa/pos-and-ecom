import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from shops.models import Shop
from shops.models import ShopType
from shops.models import ShopMigrationMapp
from shops.models import ShopPhoto
from shops.models import ShopDocument
from shops.models import ShopInvoicePattern
from shops.models import ParentRetailerMapping
from shops.models import ShopUserMapping
from addresses.models import Address
from copy import copy, deepcopy
from products.models import ProductPrice
from retailer_backend import cron


def set_shop_user_mappping(sp_shop, new_sp_shop):
    ShopUserMapping.objects.all().filter(shop=new_sp_shop).delete()
    user_mapping_list = sp_shop.shop_user.all()
    for user_mapping in user_mapping_list:
        new_user_mapping = deepcopy(user_mapping)
        new_user_mapping.pk = None
        new_user_mapping.shop = new_sp_shop
        new_user_mapping.save()


def set_related_user_invoice_parent(sp_shop, new_sp_shop):
    related_users_list = sp_shop.related_users.all()
    new_sp_shop.related_users.clear()
    for related_users in related_users_list:
        new_sp_shop.related_users.add(related_users)
    new_sp_shop.save()
    ShopInvoicePattern.objects.all().filter(shop=new_sp_shop).delete()
    invoice_pattern_list = sp_shop.invoice_pattern.all()
    print(invoice_pattern_list)
    for invoice_pattern in invoice_pattern_list:
        new_invoice_pattern = deepcopy(invoice_pattern)
        new_invoice_pattern.pk = None
        new_invoice_pattern.shop = new_sp_shop
        new_invoice_pattern.save()
    ParentRetailerMapping.objects.all().filter(retailer=new_sp_shop).delete()
    parent_list = sp_shop.retiler_mapping.all()
    for parent in parent_list:
        new_parent = deepcopy(parent)
        new_parent.pk = None
        new_parent.retailer = new_sp_shop
        new_parent.save()


def set_photo_doc_address(gf_shop, new_sp_shop):
    ShopPhoto.objects.all().filter(shop_name=new_sp_shop).delete()
    ShopDocument.objects.all().filter(shop_name=new_sp_shop).delete()
    Address.objects.all().filter(shop_name=new_sp_shop).delete()
    photos_list = gf_shop.shop_name_photos.all()
    for photos in photos_list:
        new_photos = deepcopy(photos)
        new_photos.pk = None
        new_photos.shop_name = new_sp_shop
        new_photos.save()
    document_list = gf_shop.shop_name_documents.all()
    for documents in document_list:
        new_documents = deepcopy(documents)
        new_documents.pk = None
        new_documents.shop_name = new_sp_shop
        new_documents.save()
    address_list = gf_shop.shop_name_address_mapping.all()
    for address in address_list:
        new_address = deepcopy(address)
        new_address.pk = None
        new_address.nick_name = address.nick_name + " sp"
        new_address.shop_name = new_sp_shop
        new_address.save()


def set_shop_pricing(sp_shop, new_sp_shop):
    print(new_sp_shop.pk)
    pass
    ProductPrice.objects.all().filter(seller_shop=new_sp_shop).delete()
    price_list = sp_shop.shop_product_price.all()
    for price in price_list:
        new_price = deepcopy(price)
        new_price.pk = None
        new_price.seller_shop = new_sp_shop
        new_price.save()

def set_buyer_shop_new_retailer(sp_shop, new_sp_shop):
    sp_shop.parrent_mapping.all().update(parent=new_sp_shop)



# get shop mapping
shop_mapping_list = ShopMigrationMapp.objects.all()

# create Addistro shops
sp_shop_type = ShopType.objects.all().filter(pk=3).last()





for shop_mapping in shop_mapping_list:
    gf_shop = Shop.objects.all().filter(pk=shop_mapping.gf_addistro_shop).last()
    sp_shop = Shop.objects.all().filter(pk=shop_mapping.sp_gfdn_shop).last()
    if shop_mapping.new_sp_addistro_shop == 0:
        new_sp_shop = deepcopy(sp_shop)
        new_sp_shop.pk = None
        new_sp_shop.shop_name = gf_shop.shop_name
        new_sp_shop.warehouse_code = gf_shop.warehouse_code
        new_sp_shop.save()
        shop_mapping.new_sp_addistro_shop = new_sp_shop.pk
        shop_mapping.save()
    else:
        new_sp_shop = Shop.objects.all().filter(pk=shop_mapping.new_sp_addistro_shop).last()

    # set Releated users
    set_related_user_invoice_parent(sp_shop, new_sp_shop)
    # set shop photos and documents
    set_photo_doc_address(gf_shop, new_sp_shop)

    #set shop user mapping
    set_shop_user_mappping(sp_shop,new_sp_shop)

    #For models other them shop
    set_shop_pricing(sp_shop, new_sp_shop)

    #Change existing shop parent_cat_sku_code
    set_buyer_shop_new_retailer(sp_shop,new_sp_shop)

    #sync es data

