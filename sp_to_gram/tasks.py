import sys
import os
import datetime
import json
from celery.task import task
from celery.contrib import rdb
import requests
import json
from django.db.models import F,Sum, Q
from elasticsearch import Elasticsearch
from shops.models import Shop
from sp_to_gram import models
from products.models import Product, ProductPrice
from wms.common_functions import get_stock, CommonWarehouseInventoryFunctions as CWIF, get_product_stock
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])


def get_warehouse_stock(shop_id=None,product=None):
	product_dict = None
	if shop_id:
		shop = Shop.objects.get(id=shop_id)
		if product is None:
			stock = get_stock(shop).filter(quantity__gt=0,).values('sku__id').annotate(available_qty=Sum('quantity'))
			product_dict = {g['sku__id']: g['available_qty'] for g in stock}
		else:
			stock_p=get_product_stock(shop, product)
			if stock_p:
				stock = stock_p.filter(quantity__gt=0, ).values('sku__id').annotate(available_qty=Sum('quantity'))
				product_dict = {g['sku__id']: g['available_qty'] for g in stock}
			else:
				product_dict = {product.id: 0}
		product_list = product_dict.keys()
	else:
		product_list = CWIF.filtered_warehouse_inventory_items().values('sku__id').distinct()
	products = Product.objects.filter(pk__in=product_list).order_by('product_name')
	if shop_id:
		products_price = ProductPrice.objects.filter(product__id__in=products, seller_shop=shop, status=True).order_by('product_id', '-created_at').distinct('product')
	else:
		products_price = ProductPrice.objects.filter(product__id__in=products, status=True).order_by('product_id', '-created_at').distinct('product')
	p_list = []
	for p in products_price:
		user_selected_qty = None
		no_of_pieces = None
		sub_total = None
		available_qty = 0 if shop_id else 1
		name = p.product.product_name
		mrp = p.mrp
		ptr = p.selling_price
		try:
			margin = (((p.mrp - p.selling_price) / p.mrp) * 100)
		except:
			margin = 0
		status = p.product.status
		product_opt = p.product.product_opt_product.all()
		weight_value = None
		weight_unit = None
		pack_size = None
		try:
			pack_size = p.product.product_inner_case_size if p.product.product_inner_case_size else None
		except Exception as e:
			logger.exception("pack size is not defined for {}".format(p.product.product_name))
			continue
		if product_dict:
			if int(pack_size) > int(product_dict[p.product.id]):
				status = False
			else:
				available_qty = int(int(product_dict[p.product.id])/int(pack_size))
		try:
			for p_o in product_opt:
				weight_value = p_o.weight.weight_value if p_o.weight.weight_value else None
				weight_unit = p_o.weight.weight_unit if p_o.weight.weight_unit else None
		except:
			weight_value = None
			weight_unit = None
		product_img = p.product.product_pro_image.all()
		product_images = [
			{
				"image_name":p_i.image_name,
				"image_alt":p_i.image_alt_text,
				"image_url":p_i.image.url
			}
			for p_i in product_img
		]
		category = [str(c.category) for c in p.product.product_pro_category.filter(status=True)]
		product_details = {"name":p.product.product_name,"name_lower":p.product.product_name.lower(),"brand":str(p.product.product_brand),"brand_lower":str(p.product.product_brand).lower(),"category": category, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "id":p.product_id,
						   "weight_value":weight_value,"weight_unit":weight_unit,"product_images":product_images,"user_selected_qty":user_selected_qty, "pack_size":pack_size,
						   "margin":margin ,"no_of_pieces":no_of_pieces, "sub_total":sub_total, "available": available_qty}
		yield(product_details)

def create_es_index(index):
	return "{}-{}".format(es_prefix, index)

def upload_shop_stock(shop=None,product=None):
	all_products = get_warehouse_stock(shop,product)
	es_index = shop if shop else 'all_products'
	for product in all_products:
		es.index(index=create_es_index(es_index), doc_type='product',id=product['id'], body=product)

@task
def update_shop_product_es(shop, product_id,**kwargs):
	try:
		#es.update(index=create_es_index(shop),id=product_id,body={"doc":kwargs},doc_type='product')
		##Changed to use single function for all updates
		product= Product.objects.filter(id=product_id).last()
		upload_shop_stock(shop,product)
	except Exception as e:
		pass
		#upload_shop_stock(shop)

@task
def update_product_es(shop, product_id,**kwargs):
	try:
		es.update(index=create_es_index(shop),id=product_id,body={"doc":kwargs},doc_type='product')
	except Exception as e:
		pass
		#upload_shop_stock(shop)

def es_search(index, body):
	return es.search(index=create_es_index(index), body=body)
