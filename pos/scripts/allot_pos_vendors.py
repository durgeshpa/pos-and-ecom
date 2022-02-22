from datetime import datetime, timedelta

from addresses.models import Address
from pos.models import PosCart, Vendor
from retailer_to_sp.models import Order


def run():
    print('allot_pos_vendor| STARTED')

    vendors = Vendor.objects.filter(vendor_name='PepperTap', retailer_shop__isnull=True)

    for vendor in vendors:
        print(vendor.company_name)
        pos_cart_instances = PosCart.objects.filter(vendor=vendor, gf_order_no__isnull=False).\
            values('retailer_shop', 'gf_order_no').distinct()
        total_count = pos_cart_instances.count()
        print("PosCart instances, count:", total_count)
        for cnt, instance in enumerate(pos_cart_instances):
            print("\n\nProcessing ", cnt + 1, " / ", total_count)
            gf_order_no = instance['gf_order_no']
            order = Order.objects.filter(order_no=gf_order_no).last()
            print(order.pk, " > ", order.order_no, ": ", order.seller_shop, " ----> ", order.buyer_shop)
            vendor_ins, created = Vendor.objects.get_or_create(
                company_name=order.seller_shop.shop_name, retailer_shop=order.buyer_shop)
            if created:
                bill_add = Address.objects.filter(shop_name=order.seller_shop, address_type='billing').last()
                vendor_ins.vendor_name, vendor_ins.address, vendor_ins.pincode = 'PepperTap', bill_add.address_line1, bill_add.pincode
                vendor_ins.city, vendor_ins.state = bill_add.city, bill_add.state
                vendor_ins.save()
                print("Vendor created, instance: ", vendor_ins)
            else:
                print("Vendor already exists, instance: ", vendor_ins)
