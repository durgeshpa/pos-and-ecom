from pos.models import PaymentType, Payment
from shops.models import Shop, PosShopUserMapping
from accounts.models import User


def run(*args):
    # Payment Type Update
    cash_type = PaymentType.objects.get(type='cash')
    credit_type = PaymentType.objects.get(type='credit')
    online_type = PaymentType.objects.get(type='online')

    payments = Payment.objects.all()

    for payment in payments:
        if payment.payment_mode == 'cash':
            payment.payment_type = cash_type
            payment.save()
        elif payment.payment_mode == 'credit':
            payment.payment_type = credit_type
            payment.save()
        elif payment.payment_mode == 'online':
            payment.payment_type = online_type
            payment.save()
        else:
            print("Payment Type Not Found - {} - order {}".format(payment.payment_mode, payment.order.id))

    print("Payment model - payment type - updated")

    print("user migration started")

    count = 0
    shops = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, pos_enabled=True)
    created_by = User.objects.get(phone_number='7763886418')
    for shop in shops:
        rel_users = shop.related_users.all()
        if rel_users:
            for user in rel_users:
                count += 1
                mapping, created = PosShopUserMapping.objects.get_or_create(shop=shop, user=user)
                mapping.user_type = 'manager'
                if created:
                    mapping.created_by = created_by
                mapping.status = True
                mapping.save()

    print("{} user mappings created".format(count))
