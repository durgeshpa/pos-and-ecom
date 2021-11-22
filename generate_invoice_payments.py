from django.db import transaction

from accounts.models import User
from retailer_to_sp.models import OrderedProduct
from payments.models import Payment, OrderPayment, ShipmentPayment

def generate_payment_entries(*args, **kwargs):
    try:
        user = User.objects.get(phone_number=7763886418)
        processed_by = user
        shipments = OrderedProduct.objects.all()
        for shipment in shipments:
            try:
                invoice_amount = shipment.invoice_amount
                paid_by = shipment.order.buyer_shop.shop_owner          

                with transaction.atomic():
                        paid_amount = invoice_amount
                        payment_mode_name = "cash_payment"
                        # create payment
                        payment = Payment.objects.create(
                            paid_amount = paid_amount,
                            payment_mode_name = payment_mode_name,
                            paid_by = paid_by,
                            processed_by = processed_by
                            )

                        # create order payment
                        order_payment = OrderPayment.objects.create(
                            paid_amount = paid_amount,
                            parent_payment = payment,
                            order = shipment.order,
                            created_by = processed_by,
                            updated_by = processed_by
                            )
                        
                        # create shipment payment
                        shipment_payment = ShipmentPayment.objects.create(
                            paid_amount = paid_amount,
                            parent_order_payment = order_payment,
                            shipment = shipment,
                            created_by = processed_by,
                            updated_by = processed_by                        
                            )
                print ("Payment entry created successfully for invoice id: " + str(shipment.id))        
            except Exception as e:
                print ("Error while generating payment for shipment id: " +  str(shipment.id) + " : " + str(e))
        print ("All entries created successfully!")        
    except Exception as e:
        print ("Error while generating the payment: " + str(e))

if __name__ == '__main__':
    generate_payment_entries()
