import datetime
import io
import logging

import xlsxwriter
from django.db import transaction
from django.http import HttpResponse

from retailer_incentive.common_validators import bulk_incentive_data_validation
from retailer_incentive.models import SchemeShopMapping, IncentiveDashboardDetails, Incentive, BulkIncentive

today_date = datetime.date.today()

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')

def get_active_mappings(shop_id):
    """
    Returns the queryset of active mappings for the given shop
    Params:
        shop_id : id of the shop
    """
    return SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True)


def get_shop_scheme_mapping(shop_id):
    """Returns the valid Scheme mapped for given shop_id"""
    current_year = today_date.year
    current_month = today_date.month
    shop_scheme_mapping_qs = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True,
                                                              start_date__year=current_year,
                                                              start_date__month=current_month,
                                                              end_date__year=current_year,
                                                              end_date__month=current_month)
    if shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).exists():
        return shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).last()
    return shop_scheme_mapping_qs.last()


def get_shop_scheme_mapping_based(shop_id, month):
    """Returns the valid Scheme mapped for given shop_id based on selected month (current_month)"""
    current_year = today_date.year
    scheme_shop_mapping_list = []
    if month == today_date.month:
        var_priority = 'priority'
        shop_scheme_mapping_qs = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True,
                                                                  start_date__year=current_year,
                                                                  end_date__year=current_year,
                                                                  start_date__month=month,
                                                                  end_date__month=month).order_by('-start_date',
                                                                                                  var_priority)
        if shop_scheme_mapping_qs:
            start_end_date_list = []
            for scheme in shop_scheme_mapping_qs:
                start_end_date = str(scheme.start_date) + str(scheme.end_date)
                if start_end_date in start_end_date_list:
                    continue
                start_end_date_list += [start_end_date]
                scheme_shop_mapping_list.append(scheme)
        var_priority = 'scheme_priority'
        shop_scheme_mapping_qs = IncentiveDashboardDetails.objects.filter(shop_id=shop_id,
                                                                          start_date__year=current_year,
                                                                          end_date__year=current_year,
                                                                          start_date__month=month,
                                                                          end_date__month=month).order_by('-start_date',
                                                                                                          var_priority)
        if shop_scheme_mapping_qs:
            start_end_date_list = []
            for scheme in shop_scheme_mapping_qs:
                start_end_date = str(scheme.start_date) + str(scheme.end_date)
                if start_end_date in start_end_date_list:
                    continue
                start_end_date_list += [start_end_date]
                scheme_shop_mapping_list.append(scheme)
        return scheme_shop_mapping_list
    else:
        var_priority = 'scheme_priority'
        shop_scheme_mapping_qs = IncentiveDashboardDetails.objects.filter(shop_id=shop_id,
                                                                          start_date__year=current_year,
                                                                          end_date__year=current_year,
                                                                          start_date__month=month,
                                                                          end_date__month=month).order_by('-start_date',
                                                                                                          var_priority)

        if shop_scheme_mapping_qs:
            start_end_date_list = []
            scheme_shop_mapping_list = []
            for scheme in shop_scheme_mapping_qs:
                start_end_date = str(scheme.start_date) + str(scheme.end_date)
                if start_end_date in start_end_date_list:
                    continue
                start_end_date_list += [start_end_date]
                scheme_shop_mapping_list.append(scheme)
    return scheme_shop_mapping_list


def pos_save_file(bulk_incentive_obj):
    response_file = None
    if bulk_incentive_obj:
        if bulk_incentive_obj.uploaded_file:
            error_list, validated_rows = bulk_incentive_data_validation(bulk_incentive_obj.uploaded_file)
            if validated_rows:
                bulk_create_incentives(validated_rows, bulk_incentive_obj.uploaded_by)
            if len(error_list) > 1:
                response_file = error_incentives_xlsx(error_list, bulk_incentive_obj)
    return response_file


def bulk_create_incentives(data, uploaded_by):
    with transaction.atomic():
        for row in data:
            try:
                Incentive.objects.create(
                    shop_id=row[0], capping_applicable=row[2],capping_value=row[3], date_of_calculation=row[4],
                    total_ex_tax_delivered_value=row[5], incentive=row[6], created_by=uploaded_by,
                    updated_by=uploaded_by)
            except Exception as e:
                info_logger.info("BulkCreateIncentiveView | can't create Incentive", e.args)


def error_incentives_xlsx(list_data, bulk_incentive_obj):
    filename = f'incentive_error_sheet_{bulk_incentive_obj.pk}.xlsx'
    info_logger.info("creating xlsx for wrong data.")
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({'bold': True})

    # Write error msg in xlsx sheet.
    for row_num, columns in enumerate(list_data):
        for col_num, cell_data in enumerate(columns):
            worksheet.write(row_num, col_num, cell_data, bold if row_num == 0 else None)
    workbook.close()
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response

