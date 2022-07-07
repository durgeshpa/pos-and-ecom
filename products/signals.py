from decimal import Decimal

from products.common_function import get_b2c_product_details
from products.models import Product, ProductPrice, ProductCategory, \
    ProductTaxMapping, ProductImage, ParentProductTaxMapping, ParentProduct, Repackaging, SlabProductPrice, PriceSlab, \
    ProductPackingMapping, DestinationRepackagingCostMapping, ProductSourceMapping, ProductB2cCategory, \
    ParentProductB2cCategory, ParentProductCategory, ParentProductSKUGenerator, SuperStoreProductPrice, \
    SuperStoreProductPriceLog
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from sp_to_gram.tasks import update_shop_product_es, update_product_es, update_shop_product_es_cat, \
    update_shop_product_es_brand, create_es_index
from analytics.post_save_signal import get_category_product_report
import logging
from django.db import transaction
from wms.models import Out, In, InventoryType, Pickup, WarehouseInventory, InventoryState, BinInventory, \
    PutawayBinInventory, Putaway
from retailer_to_sp.models import generate_picklist_id, PickerDashboard
from wms.common_functions import CommonPickupFunctions, CommonPickBinInvFunction, InternalInventoryChange, \
    CommonWarehouseInventoryFunctions, update_visibility, get_visibility_changes, get_manufacturing_date, \
    CommonBinInventoryFunctions
from datetime import datetime
from shops.models import Shop
from retailer_backend import common_function
from brand.models import Brand
from categories.models import Category, B2cCategory
from global_config.models import GlobalConfig
from retailer_backend.settings import es

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


@receiver(post_save, sender=PriceSlab)
def update_elasticsearch_on_price_slab_add(sender, instance=None, created=False, **kwargs):
    info_logger.info("Inside update_elasticsearch_on_price_slab_add, instance: " + str(instance))
    product = Product.objects.filter(pk=instance.product_price.product.id).last()
    if product.status != 'active' and instance.product_price.approval_status == 2 and instance.product_price.status and \
            product.repackaging_type == Product.NONE:
        info_logger.info("Inside update_elasticsearch, update active flag for instance: " + str(instance))
        product.status = 'active'
        product.save()
    else:
        info_logger.info("Inside update_elasticsearch, update product visibility for instance: " + str(instance))
        update_product_visibility(instance.product_price.product.id, instance.product_price.seller_shop.id)


def update_product_visibility(product_id, shop_id):
    info_logger.info("Inside update_product_visibility, product_id: " + str(product_id) + ", shop_id: " + str(shop_id))
    product = Product.objects.filter(id=product_id).last()
    if product.parent_product.product_type == 'superstore':
        update_shop_product_es.apply_async(args=[shop_id, product_id], countdown=GlobalConfig.objects.get(
            key='celery_countdown').value)
        return
    visibility_changes = get_visibility_changes(shop_id, product_id)
    for prod_id, visibility in visibility_changes.items():
        sibling_product = Product.objects.filter(pk=prod_id).last()
        update_visibility(shop_id, sibling_product, visibility)
        if prod_id == product_id:
            update_shop_product_es.apply_async(args=[shop_id, prod_id], countdown=GlobalConfig.objects.get(
                key='celery_countdown').value)
        else:
            update_product_es.delay(shop_id, prod_id, visible=visibility)


@receiver(post_save, sender=ProductCategory)
def update_category_elasticsearch(sender, instance=None, created=False, **kwargs):
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.apply_async(args=[prod_price['seller_shop'], prod_price['product']],
                                           countdown=GlobalConfig.objects.get(key='celery_countdown').value)


@receiver(post_save, sender=ProductB2cCategory)
def update_b2c_category_elasticsearch(sender, instance=None, created=False, **kwargs):
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.apply_async(args=[prod_price['seller_shop'], prod_price['product']],
                                           countdown=GlobalConfig.objects.get(key='celery_countdown').value)


@receiver(post_save, sender=ProductImage)
def update_product_image_elasticsearch(sender, instance=None, created=False, **kwargs):
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.apply_async(args=[prod_price['seller_shop'], prod_price['product']],
                                           countdown=GlobalConfig.objects.get(key='celery_countdown').value)


@receiver(post_save, sender=Product)
def update_product_elasticsearch(sender, instance=None, created=False, **kwargs):
    if not instance.parent_product:
        info_logger.info(
            "Post Save call being cancelled for product {} because Parent Product mapping doesn't exist".format(
                instance.id))
        return
    info_logger.info("Updating Tax Mappings of product")
    for prod_price in instance.super_store_product_price.values('seller_shop', 'product'):
        update_shop_product_es.apply_async(args=[prod_price['seller_shop'], prod_price['product']],
                                           countdown=GlobalConfig.objects.get(key='celery_countdown').value)


@receiver(post_save, sender=ParentProduct)
def update_parent_product_elasticsearch(sender, instance=None, created=False, **kwargs):
    info_logger.info("Updating ES of child products of parent {}".format(instance))
    child_products = Product.objects.filter(parent_product=instance)
    for child_product in child_products:
        for prod_price in child_product.super_store_product_price.values('seller_shop', 'product'):
            update_shop_product_es.apply_async(args=[prod_price['seller_shop'], prod_price['product']],
                                               countdown=GlobalConfig.objects.get(key='celery_countdown').value)


@receiver(post_save, sender=ParentProductTaxMapping)
def update_child_product_tax_mapping(sender, instance=None, created=False, **kwargs):
    tax_type = instance.tax.tax_type
    child_skus = Product.objects.filter(parent_product=instance.parent_product)
    for child in child_skus:
        if ProductTaxMapping.objects.filter(product=child, tax=instance.tax).exists():
            continue
        if ProductTaxMapping.objects.filter(product=child, tax__tax_type=tax_type).exists():
            ProductTaxMapping.objects.filter(product=child, tax__tax_type=tax_type).update(tax=instance.tax)
        else:
            ProductTaxMapping.objects.create(
                product=child,
                tax=instance.tax
            ).save()


def update_product_tax_mapping(product):
    parent_tax_mappings = ParentProductTaxMapping.objects.filter(parent_product=product.parent_product)
    for tax_mapping in parent_tax_mappings:
        tax_type = tax_mapping.tax.tax_type
        if ProductTaxMapping.objects.filter(product=product, tax=tax_mapping.tax).exists():
            continue
        if ProductTaxMapping.objects.filter(product=product, tax__tax_type=tax_type).exists():
            ProductTaxMapping.objects.filter(product=product, tax__tax_type=tax_type).update(tax=tax_mapping.tax)
        else:
            ProductTaxMapping.objects.create(
                product=product,
                tax=tax_mapping.tax
            ).save()


def get_bin_inv_dict(bin_inv, bin_inv_dict):
    if len(bin_inv.batch_id) == 23:
        bin_inv_dict[bin_inv] = str(datetime.strptime(
            bin_inv.batch_id[17:19] + '-' + bin_inv.batch_id[19:21] + '-' + '20' + bin_inv.batch_id[21:23],
            "%d-%m-%Y"))
    else:
        bin_inv_dict[bin_inv] = str(
            datetime.strptime('30-' + bin_inv.batch_id[17:19] + '-20' + bin_inv.batch_id[19:21],
                              "%d-%m-%Y"))
    return bin_inv_dict


def repackaging_packing_material_inventory(rep_obj):
    """
        Manage Inventory Of Packing Material In Repackaging
    """
    type_normal = InventoryType.objects.filter(inventory_type="normal").last()
    state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
    state_repackaging = InventoryState.objects.filter(inventory_state='repackaging').last()

    # Packing Material Mapped To Destination SKU
    ppm = ProductPackingMapping.objects.get(sku=rep_obj.destination_sku)
    weight = rep_obj.destination_sku_quantity * ppm.packing_sku_weight_per_unit_sku
    packing_sku = ppm.packing_sku
    shop = rep_obj.seller_shop

    # Moving Warehouse Inventory From Total Available To Repackaging State
    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
        shop, packing_sku, type_normal, state_total_available, 0, 'repackaging', rep_obj.id, True, -1 * weight)

    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
        shop, packing_sku, type_normal, state_repackaging, 0, 'repackaging', rep_obj.id, True, weight)

    # Check And Move Bin Inventory
    bin_inv_dict = {}
    bin_lists = BinInventory.objects.filter(quantity__gt=0, warehouse=rep_obj.seller_shop, sku=ppm.packing_sku,
                                            inventory_type__inventory_type='normal').order_by('-batch_id', 'quantity')
    if bin_lists.exists():
        for k in bin_lists:
            bin_inv_dict = get_bin_inv_dict(k, bin_inv_dict)
    else:
        bin_lists = BinInventory.objects.filter(quantity=0, warehouse=rep_obj.seller_shop, sku=ppm.packing_sku,
                                                inventory_type__inventory_type='normal').order_by('-batch_id',
                                                                                                  'quantity').last()
        bin_inv_dict = get_bin_inv_dict(bin_lists, bin_inv_dict)
    bin_inv_list = list(bin_inv_dict.items())
    bin_inv_dict = dict(sorted(dict(bin_inv_list).items(), key=lambda x: x[1]))

    # Deduct Inventory From Available Inventory In Bins
    for bin_inv in bin_inv_dict.keys():
        if weight == 0:
            break
        already_deducted = 0
        batch_id = bin_inv.batch_id if bin_inv else None
        wt_in_bin = bin_inv.weight if bin_inv else 0
        if weight - already_deducted <= wt_in_bin:
            already_deducted += weight
            remaining_wt = wt_in_bin - already_deducted
            bin_inv.weight = remaining_wt
            bin_inv.save()
            weight = 0
            Out.objects.create(warehouse=rep_obj.seller_shop, out_type='repackaging', out_type_id=rep_obj.id,
                               sku=ppm.packing_sku, batch_id=batch_id, weight=already_deducted, quantity=0,
                               inventory_type=type_normal)
            InternalInventoryChange.create_bin_internal_inventory_change(rep_obj.seller_shop, ppm.packing_sku, batch_id,
                                                                         bin_inv.bin, type_normal, type_normal,
                                                                         "repackaging", rep_obj.id, 0, already_deducted)
        else:
            already_deducted = wt_in_bin
            remaining_wt = weight - already_deducted
            bin_inv.weight = 0
            bin_inv.save()
            weight = remaining_wt
            Out.objects.create(warehouse=rep_obj.seller_shop, out_type='repackaging', out_type_id=rep_obj.id,
                               sku=ppm.packing_sku, batch_id=batch_id, weight=already_deducted, quantity=0,
                               inventory_type=type_normal)
            InternalInventoryChange.create_bin_internal_inventory_change(rep_obj.seller_shop, ppm.packing_sku, batch_id,
                                                                         bin_inv.bin, type_normal, type_normal,
                                                                         "repackaging", rep_obj.id, 0, already_deducted)


@receiver(post_save, sender=Repackaging)
def create_repackaging_pickup(sender, instance=None, created=False, **kwargs):
    type_normal = InventoryType.objects.filter(inventory_type="normal").last()
    if created:
        instance.repackaging_no = common_function.repackaging_no_pattern(
            Repackaging, 'id', instance.pk,
            instance.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        instance.save()
        with transaction.atomic():
            rep_obj = Repackaging.objects.get(pk=instance.pk)
            repackage_quantity = rep_obj.source_repackage_quantity
            state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()
            state_available = InventoryState.objects.filter(inventory_state='total_available').last()
            state_repackaging = InventoryState.objects.filter(inventory_state='repackaging').last()
            warehouse_available_obj = WarehouseInventory.objects.filter(warehouse=rep_obj.seller_shop,
                                                                        sku__id=rep_obj.source_sku.id,
                                                                        inventory_type=type_normal,
                                                                        inventory_state=state_available)
            if warehouse_available_obj.exists():

                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                    rep_obj.seller_shop, rep_obj.source_sku, type_normal, state_to_be_picked, repackage_quantity,
                    'repackaging', rep_obj.repackaging_no)

                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                    rep_obj.seller_shop, rep_obj.source_sku, type_normal, state_repackaging, repackage_quantity,
                    'repackaging', rep_obj.repackaging_no)
                product_zone = rep_obj.source_sku.parent_product.product_zones.filter(
                    warehouse=rep_obj.seller_shop).last().zone

                PickerDashboard.objects.create(
                    repackaging=rep_obj,
                    picking_status="picking_pending",
                    picklist_id=generate_picklist_id("00"),
                    zone=product_zone,
                    is_clickable=True
                )
                rep_obj.source_picking_status = 'pickup_created'
                rep_obj.save()
                shop = Shop.objects.filter(id=rep_obj.seller_shop.id).last()
                CommonPickupFunctions.create_pickup_entry_with_zone(shop, product_zone, 'Repackaging',
                                                                    rep_obj.repackaging_no, rep_obj.source_sku,
                                                                    repackage_quantity, 'pickup_creation', type_normal)
                pu = Pickup.objects.filter(pickup_type_id=rep_obj.repackaging_no)
                for obj in pu:
                    bin_inv_dict = {}
                    pickup_obj = obj
                    qty = obj.quantity
                    bin_lists = obj.sku.rt_product_sku.filter(quantity__gt=0, warehouse=shop, bin__zone=obj.zone,
                                                              inventory_type__inventory_type='normal').order_by(
                        '-batch_id',
                        'quantity')
                    if not bin_lists.exists():
                        bin_lists = obj.sku.rt_product_sku.filter(warehouse=shop, quantity__gt=0,
                                                                  inventory_type__inventory_type='normal') \
                            .order_by('-batch_id', 'quantity')
                    if bin_lists.exists():
                        for k in bin_lists:
                            bin_inv_dict = get_bin_inv_dict(k, bin_inv_dict)
                    else:
                        bin_lists = obj.sku.rt_product_sku.filter(quantity=0, warehouse=shop, bin__zone=obj.zone,
                                                                  inventory_type__inventory_type='normal') \
                            .order_by('-batch_id', 'quantity').last()
                        if not bin_lists:
                            bin_lists = obj.sku.rt_product_sku.filter(quantity=0, warehouse=shop,
                                                                      inventory_type__inventory_type='normal') \
                                .order_by('-batch_id', 'quantity').last()
                        bin_inv_dict = get_bin_inv_dict(bin_lists, bin_inv_dict)

                    bin_inv_list = list(bin_inv_dict.items())
                    bin_inv_dict = dict(sorted(dict(bin_inv_list).items(), key=lambda x: x[1]))
                    for bin_inv in bin_inv_dict.keys():
                        if qty == 0:
                            break
                        already_picked = 0
                        batch_id = bin_inv.batch_id if bin_inv else None
                        qty_in_bin = bin_inv.quantity if bin_inv else 0
                        shops = bin_inv.warehouse
                        if qty - already_picked <= qty_in_bin:
                            already_picked += qty
                            remaining_qty = qty_in_bin - already_picked
                            # bin_inv.quantity = remaining_qty
                            # bin_inv.to_be_picked_qty += already_picked
                            # bin_inv.save()
                            CommonBinInventoryFunctions.move_to_to_be_picked(already_picked, bin_inv, pickup_obj.pk,
                                                                             'pickup_created')
                            qty = 0
                            Out.objects.create(warehouse=rep_obj.seller_shop,
                                               out_type='repackaging',
                                               out_type_id=rep_obj.id,
                                               sku=rep_obj.source_sku,
                                               batch_id=batch_id, quantity=already_picked,
                                               inventory_type=type_normal)
                            CommonPickBinInvFunction.create_pick_bin_inventory_with_zone(
                                shops, bin_inv.bin.zone, pickup_obj, batch_id, bin_inv,
                                quantity=already_picked,
                                bin_quantity=qty_in_bin,
                                pickup_quantity=None)
                            InternalInventoryChange.create_bin_internal_inventory_change(shops, obj.sku, batch_id,
                                                                                         bin_inv.bin,
                                                                                         type_normal, type_normal,
                                                                                         "pickup_created",
                                                                                         pickup_obj.pk,
                                                                                         already_picked)
                        else:
                            already_picked = qty_in_bin
                            remaining_qty = qty - already_picked
                            # bin_inv.quantity = qty_in_bin - already_picked
                            # bin_inv.to_be_picked_qty += already_picked
                            # bin_inv.save()
                            CommonBinInventoryFunctions.move_to_to_be_picked(already_picked, bin_inv, pickup_obj.pk,
                                                                             'pickup_created')
                            qty = remaining_qty
                            Out.objects.create(warehouse=rep_obj.seller_shop,
                                               out_type='repackaging',
                                               out_type_id=rep_obj.id,
                                               sku=rep_obj.source_sku,
                                               batch_id=batch_id, quantity=already_picked,
                                               inventory_type=type_normal)
                            CommonPickBinInvFunction.create_pick_bin_inventory_with_zone(
                                shops, bin_inv.bin.zone, pickup_obj, batch_id, bin_inv,
                                quantity=already_picked,
                                bin_quantity=qty_in_bin,
                                pickup_quantity=None)
                            InternalInventoryChange.create_bin_internal_inventory_change(shops, obj.sku, batch_id,
                                                                                         bin_inv.bin,
                                                                                         type_normal, type_normal,
                                                                                         "pickup_created",
                                                                                         pickup_obj.pk,
                                                                                         already_picked)

    else:
        rep_obj = Repackaging.objects.get(pk=instance.pk)
        with transaction.atomic():
            if rep_obj.expiry_date and not rep_obj.destination_batch_id and rep_obj.status == 'completed':
                rep_obj.destination_batch_id = '{}{}'.format(rep_obj.destination_sku.product_sku,
                                                             rep_obj.expiry_date.strftime('%d%m%y'))
                rep_obj.save()

                manufacturing_date = get_manufacturing_date(rep_obj.destination_batch_id)
                In.objects.create(warehouse=rep_obj.seller_shop, in_type='REPACKAGING',
                                  in_type_id=rep_obj.repackaging_no,
                                  sku=rep_obj.destination_sku, batch_id=rep_obj.destination_batch_id,
                                  inventory_type=type_normal,
                                  quantity=rep_obj.destination_sku_quantity, expiry_date=rep_obj.expiry_date,
                                  manufacturing_date=manufacturing_date)
                pu = Putaway.objects.create(warehouse=rep_obj.seller_shop,
                                            putaway_type='REPACKAGING',
                                            putaway_type_id=rep_obj.repackaging_no,
                                            sku=rep_obj.destination_sku,
                                            batch_id=rep_obj.destination_batch_id,
                                            inventory_type=type_normal,
                                            quantity=rep_obj.destination_sku_quantity,
                                            status=Putaway.PUTAWAY_STATUS_CHOICE.NEW,
                                            putaway_quantity=0)

                # PutawayBinInventory.objects.create(warehouse=rep_obj.seller_shop,
                #                                    sku=rep_obj.destination_sku,
                #                                    batch_id=rep_obj.destination_batch_id,
                #                                    putaway_type='REPACKAGING',
                #                                    putaway=pu,
                #                                    putaway_status=False,
                #                                    putaway_quantity=rep_obj.destination_sku_quantity)

                repackaging_packing_material_inventory(rep_obj)


@receiver(post_save, sender=ProductPackingMapping)
def update_packing_material_cost(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.packing_sku.moving_average_buying_price:
            pack_m_cost = (
                                  float(instance.packing_sku.moving_average_buying_price) / float(
                              instance.packing_sku.weight_value)) * float(instance.packing_sku_weight_per_unit_sku)

            DestinationRepackagingCostMapping.objects.filter(destination=instance.sku).update(
                primary_pm_cost=round(Decimal(pack_m_cost), 2)
            )


@receiver(post_save, sender=ProductSourceMapping)
def update_raw_material_cost_save(sender, instance=None, created=False, **kwargs):
    if created:
        source_sku_maps = ProductSourceMapping.objects.filter(destination_sku=instance.destination_sku)
        total_raw_material = 0
        count = 0
        for source_sku_map in source_sku_maps:
            source_sku = source_sku_map.source_sku
            if source_sku.moving_average_buying_price:
                count += 1
                total_raw_material += (
                                              float(source_sku.moving_average_buying_price) / float(
                                          source_sku.weight_value)) * float(instance.destination_sku.weight_value)
        raw_m_cost = total_raw_material / count if count > 0 else 0
        DestinationRepackagingCostMapping.objects.filter(destination=instance.destination_sku). \
            update(raw_material=round(Decimal(raw_m_cost), 2))


@receiver(post_delete, sender=ProductSourceMapping)
def update_raw_material_cost_delete(sender, instance=None, created=False, **kwargs):
    source_sku_maps = ProductSourceMapping.objects.filter(destination_sku=instance.destination_sku)
    total_raw_material = 0
    count = 0
    for source_sku_map in source_sku_maps:
        source_sku = source_sku_map.source_sku
        if source_sku.moving_average_buying_price:
            count += 1
            total_raw_material += (
                                          float(source_sku.moving_average_buying_price) / float(
                                      source_sku.weight_value)) * float(instance.destination_sku.weight_value)
    raw_m_cost = total_raw_material / count if count > 0 else 0
    DestinationRepackagingCostMapping.objects.filter(destination=instance.destination_sku). \
        update(raw_material=round(Decimal(raw_m_cost), 2))


post_save.connect(get_category_product_report, sender=Product)


@receiver(post_save, sender=Category)
def update_parent_category_elasticsearch(sender, instance=None, created=False, **kwargs):
    shops_str = GlobalConfig.objects.get(key='category_brand_es_shop_ids').value
    shops = str(shops_str).split(',') if shops_str else None
    update_product_on_category_update(instance, shops)

    child_categories = instance.cat_parent.all()
    for child_category in child_categories:
        child_category.save()


@receiver(post_save, sender=B2cCategory)
def update_parent_category_elasticsearch(sender, instance=None, created=False, **kwargs):
    shops_str = GlobalConfig.objects.get(key='category_brand_es_shop_ids').value
    shops = str(shops_str).split(',') if shops_str else None
    update_product_on_category_update(instance, shops, b2c=True)

    child_categories = instance.b2c_cat_parent.all()
    for child_category in child_categories:
        child_category.save()


def update_product_on_category_update(instance, shops, b2c=False):
    if b2c:
        parent_pro_categories = instance.parent_category_pro_b2c_category.all()
    else:
        parent_pro_categories = instance.parent_category_pro_category.all()
    for category in parent_pro_categories:
        parent_product = category.parent_product
        child_products = parent_product.product_parent_product.filter(status='active')
        for product in child_products:
            qs = product.product_pro_price.filter(status=True)
            qs = qs.filter(seller_shop__id__in=shops) if shops else qs
            for prod_price in qs.distinct('seller_shop').values('seller_shop', 'product'):
                update_shop_product_es_cat.delay(prod_price['seller_shop'], prod_price['product'])


@receiver(post_save, sender=Brand)
def update_parent_brand_elasticsearch(sender, instance=None, created=False, **kwargs):
    shops_str = GlobalConfig.objects.get(key='category_brand_es_shop_ids').value
    shops = str(shops_str).split(',') if shops_str else None
    update_product_on_brand_update(instance, shops)

    child_brands = instance.brand_child.all()
    for child_brand in child_brands:
        child_brand.save()


def update_product_on_brand_update(instance, shops):
    parent_products = instance.parent_brand_product.all()
    for parent_product in parent_products:
        child_products = parent_product.product_parent_product.filter(status='active')
        for product in child_products:
            qs = product.product_pro_price.filter(status=True)
            qs = qs.filter(seller_shop__id__in=shops) if shops else qs
            for prod_price in qs.distinct('seller_shop').values('seller_shop', 'product'):
                update_shop_product_es_brand.delay(prod_price['seller_shop'], prod_price['product'])


@receiver(pre_save, sender=ParentProductCategory)
def create_parent_product_id(sender, instance=None, created=False, **kwargs):
    parent_product = ParentProduct.objects.get(pk=instance.parent_product.id)
    if parent_product.parent_id:
        return
    cat_sku_code = instance.category.category_sku_part
    brand_sku_code = parent_product.parent_brand.brand_code
    last_sku = ParentProductSKUGenerator.objects.filter(cat_sku_code=cat_sku_code, brand_sku_code=brand_sku_code).last()
    if last_sku:
        last_sku_increment = str(int(last_sku.last_auto_increment) + 1).zfill(len(last_sku.last_auto_increment))
    else:
        last_sku_increment = '0001'
    ParentProductSKUGenerator.objects.create(cat_sku_code=cat_sku_code, brand_sku_code=brand_sku_code,
                                             last_auto_increment=last_sku_increment)
    parent_product.parent_id = "P%s%s%s" % (cat_sku_code, brand_sku_code, last_sku_increment)
    parent_product.save()


@receiver(pre_save, sender=ParentProductB2cCategory)
def create_parent_product_id_b2c(sender, instance=None, created=False, **kwargs):
    print('parent id generation started')
    parent_product = ParentProduct.objects.get(pk=instance.parent_product.id)
    if parent_product.parent_id:
        return
    cat_sku_code = instance.category.category_sku_part
    brand_sku_code = parent_product.parent_brand.brand_code
    last_sku = ParentProductSKUGenerator.objects.filter(cat_sku_code=cat_sku_code, brand_sku_code=brand_sku_code).last()
    if last_sku:
        last_sku_increment = str(int(last_sku.last_auto_increment) + 1).zfill(len(last_sku.last_auto_increment))
    else:
        last_sku_increment = '0001'
    ParentProductSKUGenerator.objects.create(cat_sku_code=cat_sku_code, brand_sku_code=brand_sku_code,
                                             last_auto_increment=last_sku_increment)
    parent_product.parent_id = "P%s%s%s" % (cat_sku_code, brand_sku_code, last_sku_increment)
    parent_product.save()
    print(parent_product.parent_id)


@receiver(post_save, sender=Product)
def update_product_b2c_elasticsearch(sender, instance=None, created=False, **kwargs):
    info_logger.info("Updating product in all_b2c_product")
    es_index = 'all_b2c_product'
    if instance and instance.status == 'active' and instance.parent_product.product_type != 'superstore':
        product = get_b2c_product_details(instance)
        info_logger.info(product)
        try:
            es.index(index=create_es_index(es_index), doc_type='product', id=product['id'], body=product)
            info_logger.info(
                "Inside update_product_b2c_elasticsearch, product id: " + str(product['id']) + ", product: " + str(
                    product))
        except Exception as e:
            info_logger.info("error in upload_shop_stock index creation")
            info_logger.info(e)

    else:
        try:
            es.delete(index=create_es_index(es_index), doc_type='product', id=instance.id)
            info_logger.info(
                "Inside upload_shop_stock, deleting product from ES product id: " + str(instance) + ", product: " + str(
                    instance), )
        except Exception as e:
            info_logger.info("error in update_product_b2c_elasticsearch index creation")
            info_logger.info(e)


@receiver(pre_save, sender=SuperStoreProductPrice)
def create_logs_for_qc_desk_area_mapping(sender, instance=None, created=False, **kwargs):
    if not instance._state.adding:
        try:
            old_ins = SuperStoreProductPrice.objects.get(id=instance.id)
            if instance.selling_price != old_ins.selling_price:
                SuperStoreProductPriceLog.objects.create(
                    product_price_change=old_ins, old_selling_price=old_ins.selling_price,
                    new_selling_price=instance.selling_price, updated_by=instance.updated_by)
        except:
            pass


@receiver(post_save, sender=SuperStoreProductPrice)
def update_super_store_product_price_elasticsearch(sender, instance=None, created=False, **kwargs):
    info_logger.info("Inside update_super_store_product_price_elasticsearch, instance: " + str(instance))
    update_shop_product_es.apply_async(args=[instance.seller_shop.id, instance.product.id],
                                       countdown=GlobalConfig.objects.get(key='celery_countdown').value)
