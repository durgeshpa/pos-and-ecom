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
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])


def get_warehouse_stock(shop_id=None):
	grn_dict = None
	if shop_id:
	    shop = Shop.objects.get(id=shop_id)
	    grn = models.OrderedProductMapping.get_shop_stock(shop).filter(available_qty__gt=0).values('product_id').annotate(available_qty=Sum('available_qty'))
	    grn_dict = {g['product_id']:g['available_qty'] for g in grn}
	    grn_list = grn_dict.keys()

	else:
		grn_list = models.OrderedProductMapping.objects.values('product_id').distinct()
	products = Product.objects.filter(pk__in=grn_list).order_by('product_name')
	if shop_id:
		products_price = ProductPrice.objects.filter(product__in=products, shop=shop, status=True).order_by('product_id', '-created_at').distinct('product')
	else:
		products_price = ProductPrice.objects.filter(product__in=products, status=True).order_by('product_id', '-created_at').distinct('product')
	p_list = []

	for p in products_price:
		user_selected_qty = None
		no_of_pieces = None
		sub_total = None
		name = p.product.product_name
		mrp = round(p.mrp, 2) if p.mrp else p.mrp
		ptr = round(p.price_to_retailer, 2) if p.price_to_retailer else p.price_to_retailer
		loyalty_discount = round(p.loyalty_incentive, 2) if p.loyalty_incentive else p.loyalty_incentive
		cash_discount = round(p.cash_discount, 2) if p.cash_discount else p.cash_discount
		margin = round(100 - (float(ptr) * 1000000 / (float(mrp) * (100 - float(cash_discount)) * (100 - float(loyalty_discount)))), 2) if mrp and ptr else 0

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
		if grn_dict and int(pack_size) > int(grn_dict[p.product.id]):
		    continue
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
		product_details = {"name":p.product.product_name,"brand":str(p.product.product_brand),"category": category, "mrp":mrp, "ptr":ptr, "status":status, "pack_size":pack_size, "id":p.product_id, 
		                "weight_value":weight_value,"weight_unit":weight_unit,"product_images":product_images,"user_selected_qty":user_selected_qty, "pack_size":pack_size,
		               "loyalty_discount":loyalty_discount,"cash_discount":cash_discount,"margin":margin ,"no_of_pieces":no_of_pieces, "sub_total":sub_total}
		if grn_dict:
			product_details["available"] = int(grn_dict[p.product.id])
		yield(product_details)

def create_es_index(index):
	return "{}-{}".format(es_prefix, index)

def upload_shop_stock(shop=None):
	all_products = get_warehouse_stock(shop)
	es_index = shop if shop else 'all_products'
	for product in all_products:
		es.index(index=create_es_index(es_index), doc_type='product',id=product['id'], body=product)

@task
def update_shop_product_es(shop, product_id,**kwargs):
	try:
		es.update(index=create_es_index(shop),id=product_id,body={"doc":kwargs},doc_type='product')	
	except Exception as e:
		upload_shop_stock(shop)

def es_search(index, body):
	return es.search(index=create_es_index(index), body=body)

