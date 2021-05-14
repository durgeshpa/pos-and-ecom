from retailer_to_sp.models import Cart
from retailer_backend import common_function
import traceback
import sys


def run(*args):
    print("Started")
    print("")
    carts = Cart.objects.filter(cart_no__isnull=True).order_by('id')
    count = 0
    for instance in carts:
        try:
            if not instance.cart_no:
                if instance.seller_shop:
                    bill_add_id = instance.seller_shop.shop_name_address_mapping.filter(
                        address_type='billing').last().pk
                    if bill_add_id:
                        month = instance.created_at.strftime('%m')
                        year = instance.created_at.strftime('%y')
                        if int(month) < 4:
                            year = str(int(year) - 1)
                        if instance.cart_type in ['RETAIL', 'BASIC', 'AUTO']:
                            instance.cart_no = common_function.cart_no_pattern(Cart, 'cart_no', instance.pk,
                                                                               bill_add_id, year)
                        elif instance.cart_type == 'BULK':
                            instance.cart_no = common_function.cart_no_pattern_bulk(Cart, 'cart_no', instance.pk,
                                                                                    bill_add_id, year)
                        elif instance.cart_type == 'DISCOUNTED':
                            instance.cart_no = common_function.cart_no_pattern_discounted(Cart, 'cart_no', instance.pk,
                                                                                          bill_add_id, year)
                        instance.save()
                    else:
                        print("Billing address not found for cart {} {}".format(instance.id, instance.created_at))
                        print("")
                        count += 1
                else:
                    print("Seller shop not found for cart {} {}".format(instance.id, instance.created_at))
                    print("")
                    count += 1
        except Exception as e:
            print("Failed For Cart {} {}".format(instance.id, instance.created_at))
            traceback.print_exc()
            print("")
            count += 1
            break

    print("not generated count" + str(count))
