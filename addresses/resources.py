import re

from import_export import resources

from django.core.exceptions import ValidationError

from .models import Pincode
from .forms import PincodeForm


class PincodeResource(resources.ModelResource):
    class Meta:
        model = Pincode
        form = PincodeForm
        fields = ['id', 'city', 'pincode']

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        for row_id, row in enumerate(dataset):
            if not row[1]:
                raise ValidationError('Please enter valid city at row[{}]'
                                      ''.format(row_id + 2))
            if (row[2] and not re.match('^[1-9][0-9]{5}$', row[2]) or
                    not row[2]):
                raise ValidationError('Please enter valid pincode at row[{}]'
                                      ''.format(row_id + 2))
