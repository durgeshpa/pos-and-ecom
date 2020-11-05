from django.contrib.auth.models import User

from products.models import Product, ProductPrice, ProductCategory, \
    ProductTaxMapping, ProductImage, ParentProductTaxMapping, Repackaging
from django.db.models.signals import post_save
from django.dispatch import receiver
from sp_to_gram.tasks import update_shop_product_es
from analytics.post_save_signal import get_category_product_report
import logging
from django.db import transaction
from wms.models import In, InventoryType, Pickup, WarehouseInventory, InventoryState,WarehouseInternalInventoryChange, PutawayBinInventory, Putaway
from retailer_to_sp.models import generate_picklist_id, PickerDashboard
from wms.common_functions import CommonPickupFunctions, CommonPickBinInvFunction, InternalInventoryChange
from datetime import datetime
from shops.models import Shop
from retailer_backend import common_function
logger = logging.getLogger('django')

from .tasks import approve_product_price


@receiver(post_save, sender=ProductPrice)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    if instance.approval_status == sender.APPROVED:
        product_mrp = instance.mrp if instance.mrp else instance.product.product_mrp
        #approve_product_price.delay(instance.id)
        update_shop_product_es(
            instance.seller_shop.id,
            instance.product.id,
            ptr=instance.selling_price,
            mrp=product_mrp
        )


@receiver(post_save, sender=ProductCategory)
def update_category_elasticsearch(sender, instance=None, created=False, **kwargs):
    category = [str(c.category) for c in instance.product.product_pro_category.filter(status=True)]
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], category=category)



@receiver(post_save, sender=ProductImage)
def update_product_image_elasticsearch(sender, instance=None, created=False, **kwargs):
    product_images = [{
                        "image_name":instance.image_name,
                        "image_alt":instance.image_alt_text,
                        "image_url":instance.image.url
                       }]
    for prod_price in instance.product.product_pro_price.filter(status=True).values('seller_shop', 'product'):
        update_shop_product_es.delay(prod_price['seller_shop'], prod_price['product'], product_images=product_images)


@receiver(post_save, sender=Product)
def update_product_elasticsearch(sender, instance=None, created=False, **kwargs):
    logger.info("Updating Tax Mappings of product")
    update_product_tax_mapping(instance)
    logger.error("updating product to elastic search")
    # for prod_price in instance.product_pro_price.filter(status=True).values('seller_shop', 'product', 'product__product_name', 'product__product_inner_case_size', 'product__status'):
    product_categories = [str(c.category) for c in instance.parent_product.parent_product_pro_category.filter(status=True)]
    product_images = []
    if instance.use_parent_image:
        product_images = [
            {
                "image_name": p_i.image_name,
                "image_alt": p_i.image_alt_text,
                "image_url": p_i.image.url
            }
            for p_i in instance.parent_product.parent_product_pro_image.all()
        ]
    for prod_price in instance.product_pro_price.filter(status=True).values('seller_shop', 'product', 'product__product_name', 'product__status'):
        if not product_images:
            update_shop_product_es.delay(
                prod_price['seller_shop'],
                prod_price['product'],
                name=prod_price['product__product_name'],
                pack_size=instance.product_inner_case_size,
                status=True if (prod_price['product__status'] in ['active', True]) else False,
                category=product_categories
            )
        else:
            update_shop_product_es.delay(
                prod_price['seller_shop'],
                prod_price['product'],
                name=prod_price['product__product_name'],
                pack_size=instance.product_inner_case_size,
                status=True if (prod_price['product__status'] in ['active', True]) else False,
                category=product_categories,
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


@receiver(post_save, sender=Repackaging)
def create_repackaging_pickup(sender, instance=None, created=False, **kwargs):
    if created:
        instance.repackaging_no = common_function.repackaging_no_pattern(
            Repackaging, 'id', instance.pk,
            instance.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        instance.save()
        with transaction.atomic():
            rep_obj = Repackaging.objects.get(pk=instance.pk)
            repackage_quantity = rep_obj.source_repackage_quantity
            type_normal = InventoryType.objects.filter(inventory_type="normal").last()

            warehouse_available_obj = WarehouseInventory.objects.filter(warehouse=rep_obj.seller_shop,
                                                                        sku__id=rep_obj.source_sku.id,
                                                                        inventory_type=type_normal,
                                                                        inventory_state=InventoryState.objects.filter(
                                                                            inventory_state='available').last())
            if warehouse_available_obj.exists():
                w_obj = warehouse_available_obj.last()
                w_obj.quantity = w_obj.quantity - repackage_quantity
                w_obj.save()

                warehouse_product_available = WarehouseInventory.objects.filter(warehouse=rep_obj.seller_shop,
                                                                                sku__id=rep_obj.source_sku.id,
                                                                                inventory_type__inventory_type='normal',
                                                                                inventory_state__inventory_state=
                                                                                'repackaging').last()
                if warehouse_product_available:
                    available_qty = warehouse_product_available.quantity
                    warehouse_product_available.quantity = available_qty + repackage_quantity
                    warehouse_product_available.save()
                else:
                    WarehouseInventory.objects.create(warehouse=rep_obj.seller_shop,
                                                      sku=rep_obj.source_sku,
                                                      inventory_state=InventoryState.objects.filter(
                                                          inventory_state='repackaging').last(),
                                                      quantity=repackage_quantity, in_stock=True,
                                                      inventory_type=type_normal)
                WarehouseInternalInventoryChange.objects.create(warehouse=rep_obj.seller_shop,
                                                                sku=rep_obj.source_sku,
                                                                transaction_type='repackaging',
                                                                transaction_id=rep_obj.repackaging_no,
                                                                initial_type=type_normal,
                                                                final_type=type_normal,
                                                                initial_stage=InventoryState.objects.filter(
                                                                    inventory_state='available').last(),
                                                                final_stage=InventoryState.objects.filter(
                                                                    inventory_state='repackaging').last(),
                                                                quantity=repackage_quantity)

                PickerDashboard.objects.create(
                    repackaging=rep_obj,
                    picking_status="pickup_created",
                    picklist_id=generate_picklist_id("00")
                )
                rep_obj.status = 'pickup_created'
                rep_obj.save()
                shop = Shop.objects.filter(id=rep_obj.seller_shop.id).last()
                CommonPickupFunctions.create_pickup_entry(shop, 'Repackaging', rep_obj.repackaging_no,
                                                          rep_obj.source_sku, repackage_quantity, 'pickup_creation')
                pu = Pickup.objects.filter(pickup_type_id=rep_obj.repackaging_no)
                for obj in pu:
                    bin_inv_dict = {}
                    pickup_obj = obj
                    qty = obj.quantity
                    bin_lists = obj.sku.rt_product_sku.filter(quantity__gt=0,
                                                              inventory_type__inventory_type='normal').order_by(
                        '-batch_id',
                        'quantity')
                    if bin_lists.exists():
                        for k in bin_lists:
                            if len(k.batch_id) == 23:
                                bin_inv_dict[k] = str(datetime.strptime(
                                    k.batch_id[17:19] + '-' + k.batch_id[19:21] + '-' + '20' + k.batch_id[21:23],
                                    "%d-%m-%Y"))
                            else:
                                bin_inv_dict[k] = str(
                                    datetime.strptime('30-' + k.batch_id[17:19] + '-20' + k.batch_id[19:21],
                                                      "%d-%m-%Y"))
                    else:
                        bin_lists = obj.sku.rt_product_sku.filter(quantity=0,
                                                                  inventory_type__inventory_type='normal').order_by(
                            '-batch_id',
                            'quantity').last()
                        if len(bin_lists.batch_id) == 23:
                            bin_inv_dict[bin_lists] = str(datetime.strptime(
                                bin_lists.batch_id[17:19] + '-' + bin_lists.batch_id[
                                                                  19:21] + '-' + '20' + bin_lists.batch_id[21:23],
                                "%d-%m-%Y"))
                        else:
                            bin_inv_dict[bin_lists] = str(
                                datetime.strptime('30-' + bin_lists.batch_id[17:19] + '-20' + bin_lists.batch_id[19:21],
                                                  "%d-%m-%Y"))

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
                            bin_inv.save()
                            qty = 0
                            Repackaging.objects.filter(pk=instance.pk).update(source_batch_id=batch_id)
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
                            bin_inv.save()
                            qty = remaining_qty
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
        if rep_obj.expiry_date and not rep_obj.destination_batch_id and rep_obj.status == 'completed':
            rep_obj.destination_batch_id = '{}{}'.format(rep_obj.destination_sku.product_sku,
                                                         rep_obj.expiry_date.strftime('%d%m%y'))
            rep_obj.save()
            In.objects.create(warehouse=rep_obj.seller_shop, in_type='REPACKAGING', in_type_id=rep_obj.repackaging_no,
                              sku=rep_obj.destination_sku, batch_id=rep_obj.destination_batch_id, quantity=rep_obj.destination_sku_quantity, expiry_date=rep_obj.expiry_date)
            pu = Putaway.objects.create(warehouse=rep_obj.seller_shop,
                                        putaway_type='REPACKAGING',
                                        putaway_type_id=rep_obj.repackaging_no,
                                        sku=rep_obj.destination_sku,
                                        batch_id=rep_obj.destination_batch_id,
                                        quantity=rep_obj.destination_sku_quantity,
                                        putaway_quantity=0)

            PutawayBinInventory.objects.create(warehouse=rep_obj.seller_shop,
                                               sku=rep_obj.destination_sku,
                                               batch_id=rep_obj.destination_batch_id,
                                               putaway_type='REPACKAGING',
                                               putaway=pu,
                                               putaway_status=False,
                                               putaway_quantity=rep_obj.destination_sku_quantity)


post_save.connect(get_category_product_report, sender=Product)
