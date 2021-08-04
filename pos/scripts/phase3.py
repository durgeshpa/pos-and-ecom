from pos.models import PaymentType, Payment


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
