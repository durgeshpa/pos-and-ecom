from django.db.models import Sum
from retailer_to_sp.models import OrderedProductMapping

def update_shipment():
    print("Update Shipment product tax start")
    for shipment in OrderedProductMapping.objects.all():
        product_tax_query = shipment.product.product_pro_tax.values('product', 'tax', 'tax__tax_name','tax__tax_percentage')
        product_tax = {i['tax']: [i['tax__tax_name'], i['tax__tax_percentage']] for i in product_tax_query}
        product_tax['tax_sum'] = product_tax_query.aggregate(tax_sum=Sum('tax__tax_percentage'))['tax_sum']
        shipment.product_tax_json = product_tax
        shipment.save()
    print("Update Shipment product tax  end")

def inti_process():
    update_shipment()

if __name__ == "__main__":
    inti_process()





