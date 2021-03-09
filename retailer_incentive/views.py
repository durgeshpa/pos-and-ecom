import codecs
import csv
import datetime
import logging

from dal import autocomplete
from django.db.models import Q

# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render

from accounts.middlewares import get_current_user
from retailer_incentive.forms import UploadSchemeShopMappingForm
from retailer_incentive.models import SchemeShopMapping
from retailer_incentive.utils import get_active_mappings
from shops.models import Shop


info_logger = logging.getLogger('file-info')

class ShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['r','f'])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs


def get_scheme_shop_mapping_sample_csv(request):
    """
    returns sample CSV for bulk creation of shop scheme mappings
    """
    filename = "scheme_shop_mapping_sample.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(["Scheme Id", "Scheme Name", "Shop Id", "Shop Name", "Priority"])
    writer.writerow(["1", "March Munafa", "5", "Pal Shop", "P1"])
    return response

def scheme_shop_mapping_csv_upload(request):
    """
    Creates shop scheme mappings in bulk through CSV upload
    """
    if request.method == 'POST':
        form = UploadSchemeShopMappingForm(request.POST, request.FILES)

        if form.errors:
            return render(request, 'admin/retailer_incentive/bulk-create-scheme-shop-mapping.html', {'form': form})

        if form.is_valid():
            upload_file = form.cleaned_data.get('file')
            reader = csv.reader(codecs.iterdecode(upload_file, 'utf-8', errors='ignore'))
            first_row = next(reader)

            try:
                for row_id, row in enumerate(reader):
                    SchemeShopMapping.objects.create(shop_id=row[2], scheme_id=row[0],
                                                     priority=SchemeShopMapping.PRIORITY_CHOICE._identifier_map[row[4]],
                                                     is_active=True, user=get_current_user())

            except Exception as e:
                print(e)
            return render(request, 'admin/retailer_incentive/bulk-create-scheme-shop-mapping.html', {
                'form': form,
                'success': 'Scheme Shop Mapping CSV uploaded successfully !',
            })
    else:
        form = UploadSchemeShopMappingForm()
    return render(request, 'admin/retailer_incentive/bulk-create-scheme-shop-mapping.html', {'form': form})
