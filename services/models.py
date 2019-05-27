from django.db import models

# Create your models here.
class OrderReports(models.Model):
    order_invoice = models.CharField(max_length=255, null=True)
    invoice_date = models.CharField(max_length=255, null=True)
    invoice_status = models.CharField(max_length=255, null=True)
    order_id = models.CharField(max_length=255, null=True)
    order_status = models.CharField(max_length=255, null=True)
    order_date = models.CharField(max_length=255, null=True)
    order_by = models.CharField(max_length=255, null=True)
    retailer_id = models.CharField(max_length=255, null=True)
    pin_code = models.CharField(max_length=255, null=True)
    product_id = models.CharField(max_length=255, null=True)
    product_name = models.CharField(max_length=255, null=True)
    product_brand = models.CharField(max_length=255, null=True)
    product_mrp = models.CharField(max_length=255, null=True)
    product_value_tax_included = models.CharField(max_length=255, null=True)
    ordered_sku_pieces = models.CharField(max_length=255, null=True)
    shipped_sku_pieces = models.CharField(max_length=255, null=True)
    delivered_sku_pieces = models.CharField(max_length=255, null=True)
    returned_sku_pieces = models.CharField(max_length=255, null=True)
    damaged_sku_pieces = models.CharField(max_length=255, null=True)
    product_cgst = models.CharField(max_length=255, null=True)
    product_sgst = models.CharField(max_length=255, null=True)
    product_igst = models.CharField(max_length=255, null=True)
    product_cess = models.CharField(max_length=255, null=True)
    sales_person_name = models.CharField(max_length=255, null=True)
    order_type = models.CharField(max_length=255, null=True)
    campaign_name= models.CharField(max_length=255, null=True)
    discount = models.CharField(max_length=255, null=True)


    def __str__(self):
        return  "%s"%(self.order_invoice)
