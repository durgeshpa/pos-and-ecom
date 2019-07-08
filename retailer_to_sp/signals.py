import datetime

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from django.db.models import Sum

from retailer_backend.messages import ERROR_MESSAGES
from retailer_to_sp.api.v1.views import release_blocking
from shops.models import ParentRetailerMapping

from .models import OrderedProduct, PickerDashboard


@receiver(post_save, sender=OrderedProduct)
def update_picking_status(sender, instance=None, created=False, **kwargs):
    '''
    Method to update picking status 
    '''
    #assign shipment to picklist once SHIPMENT_CREATED
    if instance.shipment_status == "SHIPMENT_CREATED":
        # assign shipment to picklist
        # tbd : if manual(by searching relevant picklist id) or automated 
        picker = PickerDashboard.objects.get(order=instance.order, picking_status="picking_in_progress").update(
            shipment=instance)

    if instance.shipment_status == "READY_TO_SHIP":
        # assign picking_status to done and create new picklist id 
        picker = PickerDashboard.objects.get(shipment=instance).update(picking_status="picking_complete")

        # if more shipment required
        PickerDashboard.objects.create(
            order=instance.order,
            picking_status="picking_pending",
            picklist_id= get_random_string(12).lower(), #generate random string of 12 digits
            )


class ReservedOrder(object):
	"""docstring for ReservedOrder"""
	def __init__(
		self, seller, buyer, sp_cart, sp_cart_product_mapping,
		sp_gram_ordered_product_mapping, sp_gram_ordered_product_reserved,
		user):
		super(ReservedOrder, self).__init__()
		self.seller_shop = seller
		self.buyer_shop = buyer
		self.sp_cart = sp_cart
		self.sp_cart_product_mapping = sp_cart_product_mapping
		self.sp_gram_ordered_product_mapping = sp_gram_ordered_product_mapping
		self.sp_gram_ordered_product_reserved = sp_gram_ordered_product_reserved
		self.user = user

	def check_seller_type(self):
		if self.seller_shop.shop_type.shop_type == 'sp':
			return self.mapped_with_sp()
		if self.seller_shop.shop_type.shop_type == 'gf':
			return self.mapped_with_gf()
	
	def sp_ordered_product_details(self, product):
		ordered_product_details = self.sp_gram_ordered_product_mapping.\
			get_product_availability(
									self.seller_shop,
									product).order_by('-expiry_date')
		return ordered_product_details

	def sp_product_available_qty(self, product):
		ordered_product_details = self.sp_ordered_product_details(product)
		available_qty = ordered_product_details.aggregate(
			available_qty_sum=Sum('available_qty'))['available_qty_sum']
		if not available_qty:
			return 0
		return available_qty

	def sp_product_availability(self, product, ordered_qty):
		available_qty = self.sp_product_available_qty(product)
		if int(available_qty) >= int(ordered_qty):
			return True
		return False

	def get_user_cart(self):
		cart = self.sp_cart.objects.filter(
								last_modified_by=self.user,
								cart_status__in=['active', 'pending', 'ordered'])
		if cart.exists():
			return True, cart.last()
		return False, None

	def get_parent_mapping(self):
		parent_mapping = ParentRetailerMapping.objects.get(
										retailer=self.buyer_shop, status=True)
		return parent_mapping

	def product_reserved(self, product, ordered_qty, cart):
		parent_mapping = self.get_parent_mapping()
		ordered_product_details = self.sp_ordered_product_details(product)
		product_availability = self.sp_product_availability(product, ordered_qty)
		if product_availability:
			remaining_amount = ordered_qty
			for product_detail in ordered_product_details:
				if product_detail.available_qty <= 0:
					continue

				if remaining_amount <= 0:
					break

				if product_detail.available_qty >= remaining_amount:
					deduct_qty = remaining_amount
				else:
					deduct_qty = product_detail.available_qty

				product_detail.available_qty -= deduct_qty
				remaining_amount -= deduct_qty
				product_detail.save()

				order_product_reserved = self.sp_gram_ordered_product_reserved(
					product=product_detail.product, reserved_qty=deduct_qty)
				order_product_reserved.order_product_reserved = product_detail
				order_product_reserved.cart = cart
				order_product_reserved.reserve_status = self.\
					sp_gram_ordered_product_reserved.ORDERED
				order_product_reserved.save()

	def create(self):
		cart_exists, cart = self.get_user_cart()
		if cart_exists:
			cart_products = cart.rt_cart_list.all()
			for cart_product in cart_products:
				self.product_reserved(
					cart_product.cart_product, int(cart_product.no_of_pieces), cart)

