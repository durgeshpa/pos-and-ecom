import codecs
import csv
import datetime
import logging
from math import floor

from dal import autocomplete
from django.db.models import Q

# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render
from django.db import transaction

from accounts.middlewares import get_current_user
from retailer_incentive.common_function import get_total_sales
from retailer_incentive.forms import UploadSchemeShopMappingForm
from retailer_incentive.models import SchemeShopMapping, SchemeSlab, IncentiveDashboardDetails, Scheme
from retailer_incentive.utils import get_active_mappings
from shops.models import Shop, ParentRetailerMapping, ShopUserMapping
from retailer_backend.utils import isDateValid

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

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
    writer.writerow(["Scheme Id", "Scheme Name", "Shop Id", "Shop Name", "Priority",
                     "Shop Mapping Start Date (YYYY-MM-DD)", "Shop Mapping End Date (YYYY-MM-DD)"])
    writer.writerow(["1", "March Munafa", "5", "Pal Shop", "P1", "2021-04-30", "2021-05-01"])
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
            msg, error = 'Scheme Shop Mapping CSV uploaded successfully !', ''
            try:
                with transaction.atomic():
                    for row_id, row in enumerate(reader):
                        scheme_id = row[0]
                        shop_id = row[2]
                        priority = SchemeShopMapping.PRIORITY_CHOICE._identifier_map[row[4]]
                        start_date = isDateValid(str(row[5]) + ' 00:00:00', "%Y-%m-%d %H:%M:%S")
                        end_date = isDateValid(str(row[6]) + ' 23:59:59', "%Y-%m-%d %H:%M:%S")

                        mappings_to_deactivate = SchemeShopMapping.objects.filter(shop_id=shop_id, priority=priority,
                                                                                  is_active=True)
                        for scheme_shop_mapping in mappings_to_deactivate:
                            deactivate_scheme_mapping(scheme_shop_mapping)

                        SchemeShopMapping.objects.create(shop_id=shop_id, scheme_id=scheme_id, priority=priority,
                                                         is_active=True, user=get_current_user(), start_date=start_date,
                                                         end_date=end_date)

            except Exception as e:
                print(e)
                error_logger.error(e)
                error, msg = 'Some Error Occured. Please Try Again Later.', ''
            return render(request, 'admin/retailer_incentive/bulk-create-scheme-shop-mapping.html', {
                'form': form,
                'success': msg,
                'error': error
            })
    else:
        form = UploadSchemeShopMappingForm()
    return render(request, 'admin/retailer_incentive/bulk-create-scheme-shop-mapping.html', {'form': form})


def deactivate_expired_schemes():
    """
    Marks all the schemes as inactive where end date has passed and scheme status is still active
    """
    schemes_to_deactivate = Scheme.objects.filter(is_active=True, end_date__lt=datetime.datetime.today().date())
    info_logger.info('deactivate_expired_scheme_mappings | Total Schemes to deactivate-{}'.format(schemes_to_deactivate.count()))
    for scheme in schemes_to_deactivate:
        deactivate_scheme(scheme)


def deactivate_scheme(scheme):
    """
    Marks the scheme as inactive
    Checks for the mappings for the scheme and marks them as inactive
    """
    scheme_mappings = SchemeShopMapping.objects.filter(scheme=scheme, is_active=True)
    for scheme_mapping in scheme_mappings:
        deactivate_scheme_mapping(scheme_mapping)
    scheme.is_active = False
    scheme.save()


def deactivate_expired_scheme_mappings():
    """
    Gets all the scheme mappings where scheme mapping end date has passed
    Iterate these shop mapping,
    calculate total sales between scheme mapping start date and end date for the respective shop,
    calculate the discount based on total sales and applicable slab
    save the values and mark scheme mapping as inactive
    """
    mappings_to_deactivate = SchemeShopMapping.objects.filter(is_active=True, end_date__lt=datetime.datetime.today().date())
    info_logger.info('deactivate_expired_scheme_mappings | Total Schemes to deactivate-{}'.format(mappings_to_deactivate.count()))

    for scheme_shop_mapping in mappings_to_deactivate:
        try:
            deactivate_scheme_mapping(scheme_shop_mapping)
            info_logger.info('deactivate_expired_scheme_mappings | Scheme Mapping Id-{}, deactivated'
                             .format(scheme_shop_mapping.id))
        except Exception as e:
            info_logger.info("Exception in deactivate_expired_scheme_mappings,Scheme Mapping Id-{}, {}"
                             .format(scheme_shop_mapping.id, e))
            info_logger.error(e)

    info_logger.info('deactivate_expired_scheme_mappings | completed')


def deactivate_scheme_mapping(scheme_shop_mapping):
    """
    Marks the given scheme mapping as inactive and save the incentive data in IncentiveDashboardDetails
    """
    incentive_end_date = scheme_shop_mapping.end_date
    scheme_end_date = scheme_shop_mapping.scheme.end_date
    if scheme_end_date < incentive_end_date:
        incentive_end_date = scheme_end_date

    total_sales = get_total_sales(scheme_shop_mapping.shop_id, scheme_shop_mapping.start_date, incentive_end_date)
    scheme_slab = SchemeSlab.objects.filter(scheme=scheme_shop_mapping.scheme, min_value__lt=total_sales) \
                                    .order_by('min_value').last()
    discount_percentage = 0
    if scheme_slab is not None:
        discount_percentage = scheme_slab.discount_value
    discount_value = floor(discount_percentage * total_sales / 100)
    shop_user_mapping = scheme_shop_mapping.shop.shop_user.filter(employee_group__name='Sales Executive',
                                                                  status=True).last()
    sales_manager = None
    sales_executive = None
    if shop_user_mapping is not None:
        try:
            sales_executive = shop_user_mapping.employee
            sales_manager = shop_user_mapping.manager.employee
        except:
            sales_manager = None
            sales_executive = None
    IncentiveDashboardDetails.objects.create(shop=scheme_shop_mapping.shop, sales_manager=sales_manager,
                                             sales_executive=sales_executive,
                                             mapped_scheme=scheme_shop_mapping.scheme,
                                             purchase_value=total_sales, incentive_earned=discount_value,
                                             discount_percentage=discount_percentage,
                                             start_date=scheme_shop_mapping.start_date,
                                             end_date=incentive_end_date,
                                             scheme_priority=scheme_shop_mapping.priority)
    scheme_shop_mapping.is_active = False
    scheme_shop_mapping.save()