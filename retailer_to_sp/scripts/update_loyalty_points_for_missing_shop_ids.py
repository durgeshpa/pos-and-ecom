import logging

from marketing.models import ReferralCode
from pos.tasks import order_loyalty_points_credit
from retailer_to_sp.models import Order

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')

from pos.models import Payment


def run():
    payments = Payment.objects.filter(order__seller_shop__id__in=[44524, 33186], order__order_no__startswith='FEO',
                                      created_at__lte='2022-04-04', created_at__gte='2022-03-21').\
        exclude(order__order_status=Order.CANCELLED)
    print(payments.count())

    for payment in payments:
        if ReferralCode.is_marketing_user(payment.order.buyer):
            payment.order.points_added = order_loyalty_points_credit(payment.order.order_amount,
                                                                     payment.order.buyer.id,
                                                                     payment.order.order_no,
                                                                     'order_credit', 'order_indirect_credit',
                                                                     9, payment.order.seller_shop.id)
            payment.order.save()
