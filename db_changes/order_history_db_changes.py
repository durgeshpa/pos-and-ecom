# For Order seller and buyer shop will copy in Cart seller and buyer shop
from retailer_to_sp.models import Order,Cart

def update_cart():
    print("Retailer Cart updation start")
    orders = Order.objects.all()
    for order in orders:
        order.ordered_cart.seller_shop = order.seller_shop
        order.ordered_cart.buyer_shop = order.buyer_shop
        order.ordered_cart.save()
    print("Retailer cart updation end")

# For Product Price and no of pieces updation
def update_cart_price():
    print("CartProductMapping updation start")
    carts = Cart.objects.all()
    for cart in carts:
        for cart_pro in cart.rt_cart_list.all():
            cart_pro.cart_product_price = cart_pro.cart_product.product_pro_price.filter(shop=cart.seller_shop,status=True).last()
            cart_pro.no_of_pieces = int(cart_pro.cart_product.product_inner_case_size)*int(cart_pro.qty)
            cart_pro.save()
    print("CartProductMapping updation end")

def inti_process():
    update_cart()
    update_cart_price()

if __name__ == "__main__":
    inti_process()





