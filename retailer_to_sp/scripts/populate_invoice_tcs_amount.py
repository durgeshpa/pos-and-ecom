import datetime

from django.db.models import Sum, F, FloatField, Q

from common.constants import APRIL, ONE
from global_config.views import get_config
from retailer_to_sp.models import Invoice, RoundAmount, BuyerPurchaseData, Note
from shops.models import ShopDocument

tcs_applicable_amt = get_config('TCS_B2B_APPLICABLE_AMT', 5000000)

def run():
    populate_invoice_amount()
    populate_buyer_purchase_data()
    populate_tcs_amount()
    populate_credit_note_tcs()

def populate_invoice_amount():
    invoices = Invoice.objects.annotate(
            invoice_amount=Sum(
                F('shipment__rt_order_product_order_product_mapping__effective_price') *
                F('shipment__rt_order_product_order_product_mapping__shipped_qty'),
                output_field=FloatField())).values('id', 'invoice_no', 'invoice_amount')
    for i in invoices:
        print(i)
        if i['invoice_amount']:
            Invoice.objects.filter(pk=i['id']).update(invoice_sub_total=i['invoice_amount'],
                                                      invoice_total=i['invoice_amount'])


def populate_buyer_purchase_data():
    start_year = 2020
    # Iterate over the year and calculate buyer's seller wise total purchase
    while start_year <= 2022:
        fin_year_start_date = datetime.date(year=start_year, month=APRIL, day=ONE)
        next_fin_year_start_date = datetime.date(year=start_year+1, month=APRIL, day=ONE)
        total_purchase = Invoice.objects.filter(~Q(shipment__order__buyer_shop__id__in=[33887, 50507, 50482, 1394, 599]),
                                                shipment__order__seller_shop__id__in=[32154, 50484, 600, 50508, 1393],
                                                shipment__order__buyer_shop__isnull=False,
                                                created_at__gte=fin_year_start_date,
                                                created_at__lt=next_fin_year_start_date)\
                                        .values('shipment__order__seller_shop_id', 'shipment__order__buyer_shop_id')\
                                        .annotate(total_purchase=Sum(F('invoice_sub_total')))
        print(total_purchase)
        for data in total_purchase:
            tcs_applicable = False
            if data['total_purchase'] >= tcs_applicable_amt:
                tcs_applicable=True
            BuyerPurchaseData.objects.create(seller_shop_id=data['shipment__order__seller_shop_id'],
                                             buyer_shop_id=data['shipment__order__buyer_shop_id'],
                                             fin_year=start_year, total_purchase=data['total_purchase'],
                                             is_tcs_applicable=tcs_applicable)
        start_year += 1


def populate_tcs_amount():
    buyer_data = BuyerPurchaseData.objects.filter(total_purchase__gte=tcs_applicable_amt)
    for data in buyer_data:
        is_buyer_gstin_available = ShopDocument.objects.filter(shop_name_id=data.buyer_id,
                                                          shop_document_type=ShopDocument.GSTIN).exists()
        tcs_percent = 1
        if is_buyer_gstin_available:
            tcs_percent = 0.75
        fin_year_start_date = datetime.date(year=data.fin_year, month=APRIL, day=ONE)
        next_fin_year_start_date = datetime.date(year=data.fin_year+1, month=APRIL, day=ONE)
        invoices = Invoice.objects.filter(shipment__order__seller_shop_id=data.seller_shop_id,
                                          shipment__order__buyer_shop_id=data.buyer_id,
                                          created_at__gte=fin_year_start_date,
                                          created_at__lte=next_fin_year_start_date).order_by('-created_at')
        total_purchase = data.total_purchase
        for i in invoices:
            if total_purchase >= tcs_applicable_amt:
                i.is_tcs_applicable = True
                i.tcs_percent = tcs_percent
                i.tcs_amount = i.invoice_sub_total*tcs_percent/100
                i.invoice_total = i.invoice_sub_total*(1+tcs_percent/100)
                i.save()
                total_purchase -= i.invoice_sub_total
            else:
                break

def populate_credit_note_tcs():
    notes = Note.objects.filter(shipment__invoice__is_tcs_applicable=True)
    for note in notes:
        tcs_percent = note.shipment.invoice.tcs_percent / 100
        note.tcs_amount = note.amount * tcs_percent
        note.note_total = note.amount * (1+tcs_percent)
        note.save()