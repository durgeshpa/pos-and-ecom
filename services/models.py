from django.db import models

# Create your models here.
class OrderReport(models.Model):
    product_name= models.CharField(max_length=255, null=True)
    product_id = models.CharField(max_length=255, null=True)

    def __str__(self):
        return  "%s->%s"%(self.product_name, self.product_id)
