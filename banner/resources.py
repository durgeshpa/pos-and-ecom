import re
from import_export import resources
from django.core.exceptions import ValidationError
from .models import BannerLocation
from .forms import BannerLocationForm


class BannerLocationResource(resources.ModelResource):
    class Meta:
        model = BannerLocation
        form = BannerLocationForm
        fields = ['id', 'banner', 'buyer_shop','city','pincode']

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        for row_id, row in enumerate(dataset):
            if not row[1]:
                raise ValidationError('Please enter valid banner_id at row[{}]'
                                      ''.format(row_id + 2))
            if not (row[2] or row[3] or row[4]):
                raise ValidationError('Please enter atleast buyer_shop, city or pincode row[{}]'
                                      ''.format(row_id + 2))
