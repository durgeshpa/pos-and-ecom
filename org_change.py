import datetime
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()

from shops.models import Shop
from shops.models import ShopType, ShopMigrationMapp, ShopPhoto, ShopDocument, ShopInvoicePattern, ParentRetailerMapping
from shops.models import ShopUserMapping
from addresses.models import Address
from copy import copy, deepcopy
from products.models import ProductPrice, ProductCapping
from banner.models import BannerPosition, BannerData
from brand.models import BrandPosition, BrandData
from sp_to_gram.models import OrderedProductMapping, StockAdjustmentMapping, StockAdjustment
from offer.models import TopSKU, OfferBannerData, OfferBannerPosition, OfferBanner


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
    ProductPrice.objects.all().filter(seller_shop=new_sp_shop).delete()
    price_list = ProductPrice.objects.all().filter(seller_shop=sp_shop)
    for price in price_list:
        new_price = deepcopy(price)
        new_price.pk = None
        new_price.seller_shop = new_sp_shop
        new_price.save()


def set_top_sku(sp_shop, new_sp_shop):
    TopSKU.objects.all().filter(shop=new_sp_shop).delete()
    sku_list = TopSKU.objects.all().filter(shop=sp_shop)
    for sku in sku_list:
        new_sku = deepcopy(sku)
        new_sku.pk = None
        new_sku.shop = new_sp_shop
        new_sku.save()


def set_capping(sp_shop, new_sp_shop):
    ProductCapping.objects.all().filter(seller_shop=new_sp_shop).delete()
    capping_list = ProductCapping.objects.all().filter(seller_shop=sp_shop)
    for capping in capping_list:
        new_capping = deepcopy(capping)
        new_capping.pk = None
        new_capping.seller_shop = new_sp_shop
        new_capping.save()
    pass


def set_buyer_shop_new_retailer(sp_shop, new_sp_shop):
    sp_shop.parrent_mapping.all().update(parent=new_sp_shop)


def set_banner_brand_position(sp_shop, new_sp_shop):
    banner_position = BannerPosition.objects.all().filter(shop=new_sp_shop)
    BannerData.objects.all().filter(slot__in=banner_position).delete()
    banner_position.delete()
    banner_position_list = BannerPosition.objects.all().filter(shop=sp_shop)
    for banner_position in banner_position_list:
        new_banner_position = deepcopy(banner_position)
        new_banner_position.pk = None
        new_banner_position.shop = new_sp_shop
        new_banner_position.save()
        banner_data_list = BannerData.objects.all().filter(slot=banner_position)
        for banner_data in banner_data_list:
            new_banner_data = deepcopy(banner_data)
            new_banner_data.pk = None
            new_banner_data.slot = new_banner_position
            new_banner_data.save()
    brand_position = BrandPosition.objects.all().filter(shop=new_sp_shop)
    BrandData.objects.all().filter(slot__in=brand_position).delete()
    brand_position.delete()
    brand_position_list = BrandPosition.objects.all().filter(shop=sp_shop).all()
    for brand_position in brand_position_list:
        new_brand_position = deepcopy(brand_position)
        new_brand_position.pk = None
        new_brand_position.shop = new_sp_shop
        new_brand_position.save()
        brand_data_list = BrandData.objects.all().filter(slot=brand_position).all()
        for brand_data in brand_data_list:
            new_brand_data = deepcopy(brand_data)
            new_brand_data.pk = None
            new_brand_data.slot = new_brand_position
            new_brand_data.save()


def set_banner_position_offer(sp_shop, new_sp_shop):
    offer_banner_position = OfferBannerPosition.objects.all().filter(shop=new_sp_shop)
    OfferBannerData.objects.all().filter(slot__in=offer_banner_position).delete()
    offer_banner_position.delete()
    offer_banner_position_list = OfferBannerPosition.objects.all().filter(shop=sp_shop)
    for offer_banner_position in offer_banner_position_list:
        new_offer_banner_position = deepcopy(offer_banner_position)
        new_offer_banner_position.pk = None
        new_offer_banner_position.shop = new_sp_shop
        new_offer_banner_position.save()
        offer_banner_data_list = OfferBannerData.objects.all().filter(slot=offer_banner_position)
        for offer_banner_data in offer_banner_data_list:
            new_offer_banner_data = deepcopy(offer_banner_data)
            new_offer_banner_data.pk = None
            new_offer_banner_data.slot = new_offer_banner_position
            new_offer_banner_data.save()


def set_inventory(sp_shop, new_sp_shop):
    stock_adjustment = StockAdjustment.objects.create(shop=new_sp_shop)
    delete_grn = OrderedProductMapping.objects.all().filter(grn_product__in=new_sp_shop, ordered_product=None)
    StockAdjustmentMapping.objects.all().filter(grn_product__in=delete_grn).delete()
    delete_grn.delete()
    grn_list = OrderedProductMapping.objects.distinct('product').filter(shop=sp_shop)
    manufacture_date = datetime.datetime.today()
    expiry_date = datetime.datetime.today() + datetime.timedelta(days=180)
    count = 0
    for grn in grn_list:
        adjustment_grn = OrderedProductMapping.objects.create(
            product=grn.product,
            shop=new_sp_shop,
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            available_qty=0,
            damaged_qty=0
        )
        StockAdjustmentMapping.objects.create(
            stock_adjustment=stock_adjustment,
            grn_product=adjustment_grn,
            adjustment_type=StockAdjustmentMapping.INCREMENT,
            adjustment_qty=0
        )
        print(count)
        count += 1


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

    # set shop user mapping
    set_shop_user_mappping(sp_shop, new_sp_shop)

    # For models other them shop
    set_shop_pricing(sp_shop, new_sp_shop)

    # Change existing shop parent_cat_sku_code
    set_buyer_shop_new_retailer(sp_shop, new_sp_shop)

    # Copy banner position
    set_banner_brand_position(sp_shop, new_sp_shop)
    # Copy Top Sku and offer banner
    set_top_sku(sp_shop, new_sp_shop)
    set_banner_position_offer(sp_shop, new_sp_shop)
    # copy inventory
    set_inventory(sp_shop, new_sp_shop)
    # copy_capping
    set_capping(sp_shop, new_sp_shop)
