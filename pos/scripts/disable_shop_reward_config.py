from shops.models import models
from django.db import transaction
def run():
	print("Script started |disable reward configration")
	count = 0

	with transaction.atomic():
		objects = Shop.objects.filter(Q(shop_type__shop_sub_type__retailer_type_name__in=["foco", "fofo"]))
		for obj in objects:
			obj.enable_loyalty_points = False
			obj.save()
			count +=1
	print("Script finshed sucessfully ...|{} SHOP disable configration".format(count))