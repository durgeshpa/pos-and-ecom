from .models import (Bin, BinInventory, Putaway, PutawayBinInventory, Pickup, WarehouseInventory,
                     InventoryState, InventoryType, WarehouseInventoryChange, In, PickupBinInventory)

from gram_to_brand.models import GRNOrderProductMapping
from shops.models import Shop
from products.models import Product
from retailer_to_sp.models import Cart, Order, OrderedProduct
from sp_to_gram.models import OrderedProductReserved
from django.db.models import Sum, Q
from datetime import datetime
import functools
import json
from celery.task import task
from datetime import datetime, timedelta


def stock_decorator(wid, skuid):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ava = BinInventory.get_filtered_bin_inventories(warehouse__id=wid, sku__id=skuid)
            print(ava)
            return func(*args, **kwargs)
        return wrapper
    return actual_decorator


def get_brand_in_shop_stock(shop_id, brand):
    shop_stock = WarehouseInventory.objects.filter(
        Q(warehouse__id=shop_id),
        Q(quantity__gt=0),
        Q(sku__product_brand__brand_parent=brand))

    return shop_stock


def get_stock(shop):
    return WarehouseInventory.objects.filter(
        Q(warehouse=shop),
        Q(quantity__gt=0),
        Q(in_stock='t')
    )


def get_warehouse_product_availability(sku_id, shop_id=False):
    # For getting stock of a sku for a particular warehouse when shop_id is given else stock of sku for all warehouses
    """
    :param shop_id:
    :param sku_id:
    :return:
    """

    if shop_id:
        product_availability = WarehouseInventory.objects.filter(
            Q(sku__id=sku_id),
            Q(warehouse__id=shop_id),
            Q(quantity__gt=0),
            Q(in_stock='t')
        ).aggregate(total=Sum('quantity')).get('total')

        return product_availability

    else:
        product_availability = WarehouseInventory.objects.filter(
            Q(sku__id=sku_id),
            Q(quantity__gt=0),
            Q(in_stock='t')
        ).aggregate(total=Sum('quantity')).get('total')

        return product_availability


class OrderManagement(object):

    @classmethod
    @task
    def create_reserved_order(cls,reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        products = params['products']
        transaction_type = params['transaction_type']

        for prod_id, ordered_qty in products.items():
            WarehouseInventory.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                              sku=Product.objects.get(id=int(prod_id)),
                                              inventory_type=InventoryType.objects.filter(inventory_type='normal').last(),
                                              inventory_state=InventoryState.objects.filter(inventory_state='reserved').last(),
                                              quantity=ordered_qty, in_stock='t')
            win = WarehouseInventory.objects.filter(sku__id=int(prod_id), quantity__gt=0,
                                                    inventory_state__inventory_state='available').order_by('created_at')
            WarehouseInventoryChange.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                    sku=Product.objects.get(id=int(prod_id)),
                                                    transaction_type=transaction_type,
                                                    transaction_id=transaction_id, initial_stage='available',
                                                    final_stage='reserved', quantity=ordered_qty)
            for k in win:
                wu = WarehouseInventory.objects.filter(id=k.id)
                qty = wu.last().quantity
                if ordered_qty == 0:
                    break
                if ordered_qty >= qty:
                    remain = 0
                    ordered_qty = ordered_qty - qty
                    wu.update(quantity=remain)
                else:
                    qty = qty - ordered_qty
                    wu.update(quantity=qty)
                    ordered_qty = 0

    @classmethod
    @task
    def release_blocking(cls, reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        transaction_type = params['transaction_type']
        for i in sku_id:
            ordered_product_reserved = WarehouseInventory.objects.filter(
                sku__id=i, inventory_state__inventory_state='reserved')
            if ordered_product_reserved.exists():
                reserved_qty = ordered_product_reserved.last().quantity
                ordered_id = ordered_product_reserved.last().id
                wim = WarehouseInventory.objects.filter(sku__id=i,inventory_state__inventory_state='available')
                available_qty = wim.last().quantity
                wim.update(quantity=available_qty+reserved_qty)
                WarehouseInventory.objects.filter(id=ordered_id).update(quantity=0)
                WarehouseInventoryChange.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                        sku=Product.objects.get(id=i),
                                                        transaction_type=transaction_type,
                                                        transaction_id=transaction_id,
                                                        initial_stage='reserved', final_stage='available',
                                                        quantity=reserved_qty)


# def get_warehouse_stock(shop_id=None):
#     grn_dict = None
#     if shop_id:
#         shop = Shop.objects.get(id=shop_id)
#         grn = WarehouseInventory.get_shop_stock(shop).filter(available_qty__gt=0).values('product_id').annotate(available_qty=Sum('available_qty'))
# 	    grn_dict = {g['product_id']:g['available_qty'] for g in grn}
# 	    grn_list = grn_dict.keys()
#
# 	else:
# 		grn_list = models.OrderedProductMapping.objects.values('product_id').distinct()
# 	products = Product.objects.filter(pk__in=grn_list).order_by('product_name')
# 	if shop_id:
# 		products_price = ProductPrice.objects.filter(product__in=products, seller_shop=shop, status=True).order_by('product_id', '-created_at').distinct('product')
# 	else:
# 		products_price = ProductPrice.objects.filter(product__in=products, status=True).order_by('product_id', '-created_at').distinct('product')
# 	p_list = []
#
# 	for p in products_price:
# 		user_selected_qty = None
# 		no_of_pieces = None
# 		sub_total = None
# 		available_qty = 0 if shop_id else 1
# 		name = p.product.product_name
# 		mrp = p.mrp
# 		ptr = p.selling_price
# 		try:
# 			margin = (((p.mrp - p.selling_price) / p.mrp) * 100)
# 		except:
# 			margin = 0
#
# 		status = p.product.status
# 		product_opt = p.product.product_opt_product.all()
# 		weight_value = None
# 		weight_unit = None
# 		pack_size = None
# 		try:
# 		    pack_size = p.product.product_inner_case_size if p.product.product_inner_case_size else None
# 		except Exception as e:
# 		    logger.exception("pack size is not defined for {}".format(p.product.product_name))
# 		    continue
# 		if grn_dict:
# 			if int(pack_size) > int(grn_dict[p.product.id]):
# 				status = False
# 			else:
# 				available_qty = int(int(grn_dict[p.product.id])/int(pack_size))
# 		try:
# 		    for p_o in product_opt:
# 		        weight_value = p_o.weight.weight_value if p_o.weight.weight_value else None
# 		        weight_unit = p_o.weight.weight_unit if p_o.weight.weight_unit else None
# 		except:
# 		    weight_value = None
# 		    weight_unit = None
# 		product_img = p.product.product_pro_image.all()
# 		product_images = [
# 		                    {
# 		                        "image_name":p_i.image_name,
# 		                        "image_alt":p_i.image_alt_text,
# 		                        "image_url":p_i.image.url
# 		                    }
# 		                    for p_i in product_img
# 		                ]
# 		category = [str(c.category) for c in p.product.product_pro_category.filter(status=True)]
# 		product_details = {"name":p.product.product_name,"name_lower":p.product.product_name.lower(),"brand":str(p.product.product_brand),"brand_lower":str(p.product.product_brand).lower(),"category": category, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "id":p.product_id,
# 		                "weight_value":weight_value,"weight_unit":weight_unit,"product_images":product_images,"user_selected_qty":user_selected_qty, "pack_size":pack_size,
# 		               "margin":margin ,"no_of_pieces":no_of_pieces, "sub_total":sub_total, "available": available_qty}
# 		yield(product_details)














