from shops.models import Shop
from django.db.models import Q
def run():
	print("Script started |disable reward configration")
	objects = Shop.objects.filter(Q(shop_type__shop_sub_type__retailer_type_name__in=["foco", "fofo"])).update(enable_loyalty_points=False)
	print("Script finshed sucessfully ...|SHOP disable configration")