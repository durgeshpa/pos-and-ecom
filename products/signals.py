from django.contrib.auth.models import User
from decimal import Decimal

from products.models import Product, ProductPrice, ProductCategory, \
    ProductTaxMapping, ProductImage, ParentProductTaxMapping, ParentProduct, Repackaging, SlabProductPrice, PriceSlab,\
    ProductPackingMapping, DestinationRepackagingCostMapping, ProductSourceMapping
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from sp_to_gram.tasks import update_shop_product_es, update_product_es
from analytics.post_save_signal import get_category_product_report
import logging
from django.db import transaction
from wms.models import Out, In, InventoryType, Pickup, WarehouseInventory, InventoryState, BinInventory, PutawayBinInventory, Putaway
from retailer_to_sp.models import generate_picklist_id, PickerDashboard
from wms.common_functions import CommonPickupFunctions, CommonPickBinInvFunction, InternalInventoryChange, \
    CommonWarehouseInventoryFunctions,update_visibility, get_visibility_changes
from datetime import datetime
from shops.models import Shop
from retailer_backend import common_function
logger = logging.getLogger('django')

from .tasks import approve_product_price


@receiver(post_save, sender=ProductPrice)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    update_shop_product_es(instance.seller_shop.id, instance.product.id)
    visibility_changes = get_visibility_changes(instance.seller_shop.id, instance.product.id)
    for prod_id, visibility in visibility_changes.items():
        sibling_product = Product.objects.filter(pk=prod_id).last()
        update_visibility(instance.seller_shop.id, sibling_product, visibility)
        if prod_id == instance.product.id:
            update_shop_product_es.delay(instance.seller_shop.id, prod_id)
        else:
            update_product_es.delay(instance.seller_shop.id, prod_id, visible=visibility)


@receiver(post_save, sender=SlabProductPrice)
def update_elasticsearch_on_price_update(sender, instance=None, created=False, **kwargs):
    shop_id = instance.seller_shop.id
    product_id = instance.product.id
    update_product_visibility(product_id, shop_id)


@receiver(post_save, sender=PriceSlab)
def update_elasticsearch_on_price_slab_add(sender, instance=None, created=False, **kwargs):
    shop_id = instance.product_price.seller_shop.id
    product_id = instance.product_price.product.id
    update_product_visibility(product_id, shop_id)


def update_product_visibility(product_id, shop_id):
    update_shop_product_es(shop_id, product_id)
    visibility_changes = get_visibility_changes(shop_id, product_id)
    for prod_id, visibility in visibility_changes.items():
        sibling_product = Product.objects.filter(pk=prod_id).last()
        update_visibility(shop_id, sibling_product, visibility)
        if prod_id == product_id:
            update_shop_product_es.delay(shop_id, prod_id)
        else:
            update_product_es.delay(shop_id, prod_id, visible=visibility)


@receiver(post_save, sender=ProductCategory)
def update_category_elasticsearch(sender, instance=None, created=False, **kwargs):
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'])



@receiver(post_save, sender=ProductImage)
def update_product_image_elasticsearch(sender, instance=None, created=False, **kwargs):
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'])


@receiver(post_save, sender=Product)
def update_product_elasticsearch(sender, instance=None, created=False, **kwargs):
    if not instance.parent_product:
        logger.info("Post Save call being cancelled for product {} because Parent Product mapping doesn't exist".format(instance.id))
        return
    logger.info("Updating Tax Mappings of product")
    update_product_tax_mapping(instance)
    for prod_price in instance.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        logger.info(prod_price)
        visibility_changes = get_visibility_changes(prod_price['seller_shop'], prod_price['product'])
        for prod_id, visibility in visibility_changes.items():
            sibling_product = Product.objects.filter(pk=prod_id).last()
            update_visibility(prod_price['seller_shop'], sibling_product, visibility)
            if prod_id == prod_price['product']:
                update_shop_product_es.delay(prod_price['seller_shop'], prod_id)
            else:
                update_product_es.delay(prod_price['seller_shop'], prod_id, visible=visibility)



@receiver(post_save, sender=ParentProduct)
def update_parent_product_elasticsearch(sender, instance=None, created=False, **kwargs):
    logger.info("Updating ES of child products of parent {}".format(instance))
    child_skus = Product.objects.filter(parent_product=instance)
    child_categories = [str(c.category) for c in instance.parent_product_pro_category.filter(status=True)]
    for child in child_skus:
        product_images = []
        if child.use_parent_image:
            product_images = [
                {
                    "image_name": p_i.image_name,
                    "image_alt": p_i.image_alt_text,
                    "image_url": p_i.image.url
                }
                for p_i in instance.parent_product_pro_image.all()
            ]
        for prod_price in child.product_pro_price.filter(status=True).values('seller_shop', 'product', 'product__product_name', 'product__status'):
            if not product_images:
                update_shop_product_es.delay(
                    prod_price['seller_shop'],
                    prod_price['product'],
                    name=prod_price['product__product_name'],
                    pack_size=instance.inner_case_size,
                    status=True if (prod_price['product__status'] in ['active', True]) else False,
                    category=child_categories
                )
            else:
                update_shop_product_es.delay(
                    prod_price['seller_shop'],
                    prod_price['product'],
                    name=prod_price['product__product_name'],
                    pack_size=instance.inner_case_size,
                    status=True if (prod_price['product__status'] in ['active', True]) else False,
                    category=child_categories,
                    product_images=product_images
                )


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

                PickerDashboard.objects.create(
                    repackaging=rep_obj,
                    picking_status="picking_pending",
                    picklist_id=generate_picklist_id("00")
                )
                rep_obj.source_picking_status = 'pickup_created'
                rep_obj.save()
                shop = Shop.objects.filter(id=rep_obj.seller_shop.id).last()
                CommonPickupFunctions.create_pickup_entry(shop, 'Repackaging', rep_obj.repackaging_no,
                                                          rep_obj.source_sku, repackage_quantity, 'pickup_creation',
                                                          type_normal)
                pu = Pickup.objects.filter(pickup_type_id=rep_obj.repackaging_no)
                for obj in pu:
                    bin_inv_dict = {}
                    pickup_obj = obj
                    qty = obj.quantity
                    bin_lists = obj.sku.rt_product_sku.filter(quantity__gt=0, warehouse=shop,
                                                              inventory_type__inventory_type='normal').order_by(
                        '-batch_id',
                        'quantity')
                    if bin_lists.exists():
                        for k in bin_lists:
                            bin_inv_dict = get_bin_inv_dict(k, bin_inv_dict)
                    else:
                        bin_lists = obj.sku.rt_product_sku.filter(quantity=0, warehouse=shop,
                                                                  inventory_type__inventory_type='normal').order_by(
                            '-batch_id',
                            'quantity').last()
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
                            bin_inv.quantity = remaining_qty
                            bin_inv.to_be_picked_qty += already_picked
                            bin_inv.save()
                            qty = 0
                            Out.objects.create(warehouse=rep_obj.seller_shop,
                                               out_type='repackaging',
                                               out_type_id=rep_obj.id,
                                               sku=rep_obj.source_sku,
                                               batch_id=batch_id, quantity=already_picked,
                                               inventory_type=type_normal)
                            CommonPickBinInvFunction.create_pick_bin_inventory(shops, pickup_obj, batch_id, bin_inv,
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
                            bin_inv.quantity = qty_in_bin - already_picked
                            bin_inv.to_be_picked_qty += already_picked
                            bin_inv.save()
                            qty = remaining_qty
                            Out.objects.create(warehouse=rep_obj.seller_shop,
                                               out_type='repackaging',
                                               out_type_id=rep_obj.id,
                                               sku=rep_obj.source_sku,
                                               batch_id=batch_id, quantity=already_picked,
                                               inventory_type=type_normal)
                            CommonPickBinInvFunction.create_pick_bin_inventory(shops, pickup_obj, batch_id, bin_inv,
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
                In.objects.create(warehouse=rep_obj.seller_shop, in_type='REPACKAGING', in_type_id=rep_obj.repackaging_no,
                                  sku=rep_obj.destination_sku, batch_id=rep_obj.destination_batch_id,
                                  inventory_type=type_normal,
                                  quantity=rep_obj.destination_sku_quantity, expiry_date=rep_obj.expiry_date)
                pu = Putaway.objects.create(warehouse=rep_obj.seller_shop,
                                            putaway_type='REPACKAGING',
                                            putaway_type_id=rep_obj.repackaging_no,
                                            sku=rep_obj.destination_sku,
                                            batch_id=rep_obj.destination_batch_id,
                                            inventory_type=type_normal,
                                            quantity=rep_obj.destination_sku_quantity,
                                            putaway_quantity=0)

                PutawayBinInventory.objects.create(warehouse=rep_obj.seller_shop,
                                                   sku=rep_obj.destination_sku,
                                                   batch_id=rep_obj.destination_batch_id,
                                                   putaway_type='REPACKAGING',
                                                   putaway=pu,
                                                   putaway_status=False,
                                                   putaway_quantity=rep_obj.destination_sku_quantity)

                repackaging_packing_material_inventory(rep_obj)


@receiver(post_save, sender=ProductPackingMapping)
def update_packing_material_cost(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.packing_sku.moving_average_buying_price:
            pack_m_cost = (
                                  float(instance.packing_sku.moving_average_buying_price) / float(instance.packing_sku.weight_value)) * float(instance.packing_sku_weight_per_unit_sku)

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
                                              float(source_sku.moving_average_buying_price) / float(source_sku.weight_value)) * float(instance.destination_sku.weight_value)
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
                                          float(source_sku.moving_average_buying_price) / float(source_sku.weight_value)) * float(instance.destination_sku.weight_value)
    raw_m_cost = total_raw_material / count if count > 0 else 0
    DestinationRepackagingCostMapping.objects.filter(destination=instance.destination_sku). \
        update(raw_material=round(Decimal(raw_m_cost), 2))


post_save.connect(get_category_product_report, sender=Product)
