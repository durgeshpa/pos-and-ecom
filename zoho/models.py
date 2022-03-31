from django.contrib.auth import get_user_model
from django.db import models

# Create your models here.
from categories.models import BaseTimeModel


class ZohoFileUpload(BaseTimeModel):
    file = models.FileField(upload_to='zoho/zoho_files/')
    upload_type = models.CharField(max_length=50, default='')
    updated_by = models.ForeignKey(
        get_user_model(), null=True, related_name='zoho_file_uploaded_by',
        on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return f"BulkUpload for Zoho File Upload updated at {self.created_at} by {self.updated_by}"


# class ZohoCreditNote(models.Model):
#     pass


# class ZohoInvoice(models.Model):
#     pass


# class ZohoCustomers(models.Model):
# pass
    

