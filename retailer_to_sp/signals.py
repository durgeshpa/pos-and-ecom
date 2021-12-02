
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum

from shops.models import ParentRetailerMapping
from .models import CartProductMapping, Cart, Trip, OrderedProduct, ShipmentPackaging
from pos.offers import BasicCartOffers
from retailer_backend import common_function


# @receiver(post_save, sender=OrderedProduct)
# def update_picking_status(sender, instance=None, created=False, **kwargs):
#     '''
#     Method to update picking status 
#     '''
#     #assign shipment to picklist once SHIPMENT_CREATED
#     if instance.shipment_status == "SHIPMENT_CREATED":
#         # assign shipment to picklist
#         # tbd : if manual(by searching relevant picklist id) or automated 
#         picker = PickerDashboard.objects.get(order=instance.order, picking_status="picking_in_progress").update(
#             shipment=instance)

#     if instance.shipment_status == "READY_TO_SHIP":
#         # assign picking_status to done and create new picklist id 
#         picker = PickerDashboard.objects.get(shipment=instance).update(picking_status="picking_complete")

#         # if more shipment required
#         PickerDashboard.objects.create(
#             order=instance.order,
#             picking_status="picking_pending",
#             picklist_id= get_random_string(12).lower(), #generate random string of 12 digits
#             )



# @receiver(post_save, sender=Order)
# def assign_picklist(sender, instance=None, created=False, **kwargs):
#     '''
#     Method to update picking status 
#     '''
#     #assign shipment to picklist once SHIPMENT_CREATED
#     if created:
#         # assign piclist to order
#         PickerDashboard.objects.create(
#             order=instance,
#             picking_status="picking_pending",
#             picklist_id= get_random_string(12).lower(), #generate random string of 12 digits
#             )
from .utils import send_sms_on_trip_start


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


@receiver(post_save, sender=CartProductMapping)
def create_offers(sender, instance=None, created=False, **kwargs):
	"""
		Update offers on cart after any product (quantity) is updated
		Check combo on product, check cart level discount
	"""
	if instance.qty and instance.no_of_pieces and instance.cart.cart_type not in ('AUTO', 'DISCOUNTED', 'BASIC', 'ECOM'):
		Cart.objects.filter(id=instance.cart.id).update(offers=instance.cart.offers_applied())
	elif instance.cart.cart_type in ['BASIC', 'ECOM'] and instance.product_type == 1 and instance.selling_price:
		# Get combo coupon for product
		offer = BasicCartOffers.get_basic_combo_coupons([instance.retailer_product.id], instance.cart.seller_shop.id)
		# Check and apply/remove combo offers
		offers_list = BasicCartOffers.basic_combo_offers(float(instance.qty), float(instance.selling_price),
														 instance.retailer_product.id, offer[0] if offer else {},
														 instance.cart.offers)
		# Recheck cart discount according to updated cart value
		offers_list = BasicCartOffers.basic_cart_offers_check(Cart.objects.get(pk=instance.cart.id), offers_list,
															  instance.cart.seller_shop.id)
		Cart.objects.filter(pk=instance.cart.id).update(offers=offers_list)


@receiver(post_delete, sender=CartProductMapping)
def remove_offers(sender, instance=None, created=False, **kwargs):
	"""
		Update offers on cart after any product is deleted
		Remove combo on this product, check cart level discount
	"""
	if instance.qty and instance.no_of_pieces and instance.cart.cart_type not in ('AUTO', 'DISCOUNTED', 'BASIC', 'ECOM'):
		Cart.objects.filter(id=instance.cart.id).update(offers=instance.cart.offers_applied())
	elif instance.cart.cart_type in ['BASIC', 'ECOM'] and instance.product_type:
		# Remove if any combo products added
		offers_list = BasicCartOffers.update_combo(instance.retailer_product.id, instance.cart.offers, [])
		# Recheck cart discount according to updated cart value
		offers_list = BasicCartOffers.basic_cart_offers_check(instance.cart, offers_list, instance.cart.seller_shop.id)
		Cart.objects.filter(pk=instance.cart.id).update(offers=offers_list)


@receiver(pre_save, sender=Cart)
def create_cart_no(sender, instance=None, created=False, **kwargs):
	if not instance.cart_no and instance.seller_shop:
		bill_add_id = instance.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk
		if instance.cart_type in ['RETAIL', 'BASIC', 'AUTO']:
			cart_no = common_function.cart_no_pattern(sender, 'cart_no', instance.pk, bill_add_id)
			while Cart.objects.filter(cart_no=cart_no).exists():
				cart_no = common_function.cart_no_pattern(sender, 'cart_no', instance.pk, bill_add_id)
			instance.cart_no = cart_no
		elif instance.cart_type in ['ECOM']:
			cart_no = common_function.cart_no_pattern(sender, 'cart_no', instance.pk, bill_add_id, 'EC')
			while Cart.objects.filter(cart_no=cart_no).exists():
				cart_no = common_function.cart_no_pattern(sender, 'cart_no', instance.pk, bill_add_id, 'EC')
			instance.cart_no = cart_no
		elif instance.cart_type == 'BULK':
			instance.cart_no = common_function.cart_no_pattern_bulk(sender, 'cart_no', instance.pk, bill_add_id)
		elif instance.cart_type == 'DISCOUNTED':
			instance.cart_no = common_function.cart_no_pattern_discounted(sender, 'cart_no', instance.pk, bill_add_id)


@receiver(post_save, sender=Trip)
def notify_customer_on_trip_start(sender, instance=None, created=False, **kwargs):
	if instance.trip_status == Trip.STARTED:
		send_sms_on_trip_start(instance)


@receiver(post_save, sender=OrderedProduct)
def mark_packages_dispatched_on_trip_start(sender, instance=None, created=False, **kwargs):
	if instance.shipment_status == OrderedProduct.OUT_FOR_DELIVERY:
		instance.shipment_packaging.filter(status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH)\
				.update(status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.DISPATCHED)
	elif instance.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
		instance.shipment_packaging.filter(status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.DISPATCHED)\
				.update(status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.READY_TO_DISPATCH)
	elif instance.shipment_status in [OrderedProduct.FULLY_DELIVERED_AND_VERIFIED,
									  OrderedProduct.FULLY_RETURNED_AND_VERIFIED,
									  OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED]:
		instance.shipment_packaging.filter(status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.DISPATCHED)\
				.update(status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.DELIVERED)




