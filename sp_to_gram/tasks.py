from celery.task import task
from elasticsearch import Elasticsearch, NotFoundError

from shops.models import Shop

from products.models import Product, ProductPrice
from wms.common_functions import get_stock, CommonWarehouseInventoryFunctions as CWIF, get_earliest_expiry_date
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix
import logging

from wms.models import InventoryType, WarehouseInventory, InventoryState

info_logger = logging.getLogger('file-info')
es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])


def create_slab_price_detail(price, mrp, case_size):
	"""Takes ProductPrice instance and returns the list of slabs for the same."""
	slab_price = []
	slabs = price.price_slabs.all().order_by('start_value')
	for slab in slabs:
		slab_price.append({
			"start_value": slab.start_value,
			"end_value": slab.end_value,
			"ptr": (slab.ptr * case_size),
			"margin": round((((float(mrp) - slab.ptr) / float(mrp)) * 100), 2)
		})
	return slab_price


def get_product_price(shop_id, products):
	"""
	Returns the dictionary of prices to be updated in ElasticSearch.
	Any product may have prices at store level, pincode level or city level
	"""
	info_logger.info("Inside get_product_price, shop_id: " + str(shop_id) + ", products: " + str(products))
	if shop_id:
		products_price = ProductPrice.objects.filter(
			product__id__in=products, seller_shop_id=shop_id, status=True, approval_status=ProductPrice.APPROVED,
			price_slabs__isnull=False).select_related('product').order_by('product_id', '-created_at')
	else:
		products_price = ProductPrice.objects.filter(
			product__id__in=products, status=True, approval_status=ProductPrice.APPROVED, price_slabs__isnull=False)\
			.select_related('product').order_by('product_id', '-created_at')
	info_logger.info("Inside get_product_price, products_price count: " + str(
		products_price.count()) + ", products_price: " + str(products_price))

	price_dict = {}
	for price in products_price:
		info_logger.info("Inside get_product_price, price: " + str(price) + ", product_mrp: " + str(
			price.product.product_mrp) + ", product_inner_case_size: " + str(price.product.product_inner_case_size))
		product_active_prices = price_dict.get(price.product_id, {'store': {}, 'pincode': {}, 'city': {}})
		if price.buyer_shop_id:
			info_logger.info("Inside get_product_price, true condition 'price.buyer_shop_id'")
			product_active_prices['store'][price.buyer_shop_id] = create_slab_price_detail(price,
																		price.product.product_mrp,
																		price.product.product_inner_case_size)
		elif price.pincode:
			info_logger.info("Inside get_product_price, true condition 'price.pincode'")
			product_active_prices['pincode'][price.pincode.pincode] = create_slab_price_detail(price,
																		price.product.product_mrp,
																		price.product.product_inner_case_size)
		elif price.city:
			info_logger.info("Inside get_product_price, true condition 'price.city'")
			product_active_prices['city'][price.city_id] = create_slab_price_detail(price,
																		price.product.product_mrp,
																		price.product.product_inner_case_size)
		elif price.seller_shop_id :
			info_logger.info("Inside get_product_price, true condition 'price.seller_shop_id '")
			product_active_prices['store'][price.seller_shop_id ] = create_slab_price_detail(price,
																		price.product.product_mrp,
																		price.product.product_inner_case_size)

		price_dict[price.product.id] = product_active_prices
	return price_dict


def get_warehouse_stock(shop_id=None, product=None, inventory_type=None):
	info_logger.info("Inside get_warehouse_stock, product: " + str(product) + ", shop_id: " + str(
		shop_id) + ", inventory_type: " + str(inventory_type))
	type_normal = InventoryType.objects.filter(inventory_type='normal').last()
	if inventory_type is None:
		inventory_type = type_normal
	product_dict = None
	if shop_id:
		shop = Shop.objects.get(id=shop_id)
		if product is None:
			product_dict = get_stock(shop, inventory_type)
		else:
			product_dict = get_stock(shop, inventory_type, [product.id])
			if not product_dict.get(product.id):
				product_dict = {product.id: 0}
		product_list = product_dict.keys()
	else:
		product_list = CWIF.filtered_warehouse_inventory_items().values('sku__id').distinct()
	products = Product.objects.filter(pk__in=product_list).order_by('product_name')
	product_price_dict = get_product_price(shop_id, products)
	info_logger.info("inside get_warehouse_stock, products: " + str(products) + ", product_price_dict: " + str(product_price_dict))
	for product in products:
		user_selected_qty = None
		no_of_pieces = None
		sub_total = None
		available_qty = 0 if shop_id else 1
		status = True if (product.status in ['active', True]) else False
		mrp = product.product_mrp
		product_price = product_price_dict.get(product.id)
		margin = 0
		ptr = 0
		pack_size = None
		try:
			pack_size = product.product_inner_case_size if product.product_inner_case_size else None
		except Exception as e:
			info_logger.exception("pack size is not defined for {}".format(product.product_name))
			continue
		price_details = []
		if product_price:
			price_details = product_price
		else:
			status = False
		product_opt = product.product_opt_product.all()
		weight_value = None
		weight_unit = None
		if product_dict:
			if int(pack_size) > int(product_dict[product.id]):
				status = False
			else:
				available_qty = int(int(product_dict[product.id]) / int(pack_size))
		try:
			for p_o in product_opt:
				weight_value = p_o.weight.weight_value if p_o.weight.weight_value else None
				weight_unit = p_o.weight.weight_unit if p_o.weight.weight_unit else None
		except:
			weight_value = None
			weight_unit = None
		if weight_unit is None:
			weight_unit = product.weight_unit
		if weight_value is None:
			weight_value = product.weight_value
		product_img = product.product_pro_image.all()
		product_images = [
			{
				"image_name": p_i.image_name,
				# "image_alt": p_i.image_alt_text,
				"image_url": p_i.image.url
			}
			for p_i in product_img
		]
		if not product_images:
			if product.use_parent_image:
				product_images = [
					{
						"image_name": p_i.image_name,
						# "image_alt": p_i.image_alt_text,
						"image_url": p_i.image.url
					}
					for p_i in product.parent_product.parent_product_pro_image.all()
				]
			else:
				product_images = [
					{
						"image_name": p_i.image_name,
						# "image_alt": p_i.image_alt_text,
						"image_url": p_i.image.url
					}
					for p_i in product.child_product_pro_image.all()
				]

		product_categories = [str(c.category) for c in
							  product.parent_product.parent_product_pro_category.filter(status=True)]
		visible=False
		if product_dict:
			visible=WarehouseInventory.objects.filter(warehouse=shop, sku=product, inventory_state=InventoryState.objects.filter(
                inventory_state='total_available').last(), inventory_type=type_normal).last()
    		if visible:
        		visible = visible.visible
		else:
			visible=True
		ean = product.product_ean_code
		if ean and type(ean) == str:
			ean = ean.split('_')[0]
		is_discounted = True if product.product_type == Product.PRODUCT_TYPE_CHOICE.DISCOUNTED else False
		expiry_date = get_earliest_expiry_date(product, shop, type_normal, is_discounted) if is_discounted else None
		product_details = {
			"sku": product.product_sku,
			"parent_id": product.parent_product.parent_id,
			"parent_name":product.parent_product.name,
			"name": product.product_name,
			"name_lower": product.product_name.lower(),
			"brand": str(product.product_brand),
			"brand_lower": str(product.product_brand).lower(),
			"category": product_categories,
			"mrp": mrp,
			"status": status,
			"id": product.id,
			"weight_value": weight_value,
			"weight_unit": weight_unit,
			"product_images": product_images,
			"user_selected_qty": user_selected_qty,
			"pack_size": pack_size,
			"margin": margin,
			"no_of_pieces": no_of_pieces,
			"sub_total": sub_total,
			"available": available_qty,
			"visible":visible,
			"ean":ean,
			"price_details" : price_details,
			"is_discounted": is_discounted,
			"expiry_date": expiry_date
		}
		info_logger.info("inside get_warehouse_stock, product_details: " + str(product_details))
		yield(product_details)


def create_es_index(index):
	return "{}-{}".format(es_prefix, index)

def upload_shop_stock(shop=None,product=None):
	info_logger.info("Inside upload_shop_stock, product: " + str(product) + ", shop: " + str(shop))
	all_products = get_warehouse_stock(shop,product)
	es_index = shop if shop else 'all_products'
	count = 0
	#if product is None:
	#	es.indices.delete(index=create_es_index(es_index), ignore=[400, 404])
	for product in all_products:
		info_logger.info(product)
		try:
			es.index(index=create_es_index(es_index), doc_type='product', id=product['id'], body=product)
			info_logger.info(
				"Inside upload_shop_stock, product id: " + str(product['id']) + ", product: " + str(product))
		except Exception as e:
			info_logger.info("error in upload_shop_stock index creation")
			info_logger.info(e)

@task
def update_shop_product_es(shop, product_id,**kwargs):
	info_logger.info("Inside update_shop_product_es, product_id: " + str(product_id) + ", shop: " + str(shop))
	try:
		#es.update(index=create_es_index(shop),id=product_id,body={"doc":kwargs},doc_type='product')
		##Changed to use single function for all updates
		product= Product.objects.filter(id=product_id).last()
		info_logger.info("Inside update_shop_product_es, product pk: " + str(product.pk) + ", shop: " + str(shop))
		upload_shop_stock(shop,product)
	except Exception as e:
		pass
		#upload_shop_stock(shop)

@task
def update_product_es(shop_id, product_id,**kwargs):
	try:
		info_logger.info("Query is")
		info_logger.info(kwargs)
		es.update(index=create_es_index(shop_id),id=product_id,body={"doc":kwargs},doc_type='product')
	except Exception as e:
		info_logger.info("exception %s",e)
		update_shop_product_es(shop_id,product_id)


def es_search(index, body):
	return es.search(index=create_es_index(index), body=body)


def es_mget_by_ids(index, body):
	return es.mget(index=create_es_index(index), body=body)


@task
def update_shop_product_es_cat(shop, product_id):
	try:
		product = Product.objects.filter(id=product_id).last()
		products_update_category_es(shop, product)
	except Exception as e:
		pass


def products_update_category_es(shop, product):
	product_category = [str(c.category) for c in product.parent_product.parent_product_pro_category.filter(status=True)]
	detail = {
		"category": product_category,
		"id": product.id,
	}
	es_index = shop if shop else 'all_products'

	info_logger.info(product.product_sku)
	try:
		es.update(index=create_es_index(es_index), doc_type='product', id=product.id, body={"doc": detail})
	except Exception as e:
		info_logger.info("error in products_update_category_es")
		info_logger.info(e)


@task
def update_shop_product_es_brand(shop, product_id):
	try:
		product = Product.objects.filter(id=product_id).last()
		products_update_brand_es(shop, product)
	except Exception as e:
		pass


def products_update_brand_es(shop, product):
	detail = {
		"brand": str(product.product_brand),
		"brand_lower": str(product.product_brand).lower(),
		"id": product.id,
	}
	es_index = shop if shop else 'all_products'

	info_logger.info(product.product_sku)
	try:
		es.update(index=create_es_index(es_index), doc_type='product', id=product.id, body={"doc": detail})
	except Exception as e:
		info_logger.info("error in products_update_brand_es")
		info_logger.info(e)
