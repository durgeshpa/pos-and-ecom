# import itertools
# import logging
#
# from products.common_function import generate_tax_group_name_by_the_mapped_taxes
# from products.models import Tax, TaxGroup, GroupTaxMapping
#
# # Logger
# info_logger = logging.getLogger('file-info')
# error_logger = logging.getLogger('file-error')
# debug_logger = logging.getLogger('file-debug')
# cron_logger = logging.getLogger('cron_log')
#
#
# def run():
#     create_tax_groups()
#
#
# def create_tax_groups():
#     """
#     This method is used to create TAX Group
#     """
#     print('create_tax_groups | STARTED')
#
#     gst_taxes = [int(x) for x in Tax.objects.filter(tax_type__iexact='gst').values_list('id', flat=True)]
#     cess_taxes = [int(x) for x in Tax.objects.filter(tax_type__iexact='cess').values_list('id', flat=True)]
#     surcharge_taxes = [int(x) for x in Tax.objects.filter(tax_type__iexact='surcharge').values_list('id', flat=True)]
#
#     # Single Taxes
#     single_taxes = list(gst_taxes) + list(cess_taxes) + list(surcharge_taxes)
#     total_single = len(single_taxes)
#     for cnt, tax_id in enumerate(single_taxes):
#         print(f"{cnt + 1}/{total_single} | {tax_id}")
#         taxes = Tax.objects.filter(id=tax_id)
#         name = generate_tax_group_name_by_the_mapped_taxes(taxes)
#         if TaxGroup.objects.filter(name=name).exists():
#             print(f"Tax group already exist with name {name}")
#             continue
#         tax_group = TaxGroup.objects.create(name=name)
#         for tax in taxes:
#             tax_map, _ = GroupTaxMapping.objects.update_or_create(tax_group=tax_group, tax=tax)
#             print(f"Tax Group Mapping created {_} | instance {tax_map}")
#
#     # Combined Taxes
#     g_c_taxes = [gst_taxes, cess_taxes]
#     g_s_taxes = [gst_taxes, surcharge_taxes]
#     c_s_taxes = [cess_taxes, surcharge_taxes]
#     all_taxes = [gst_taxes, cess_taxes, surcharge_taxes]
#     print(all_taxes)
#     all_combined_taxes = list(itertools.product(*g_c_taxes)) + list(itertools.product(*g_s_taxes)) + \
#                          list(itertools.product(*c_s_taxes)) + list(itertools.product(*all_taxes))
#     total = len(all_combined_taxes)
#     print(total, all_combined_taxes)
#
#     for cnt, tax_list in enumerate(all_combined_taxes):
#         print(f"{cnt + 1}/{total} | {tax_list}")
#         taxes = Tax.objects.filter(id__in=tax_list)
#         name = generate_tax_group_name_by_the_mapped_taxes(taxes)
#         if TaxGroup.objects.filter(name=name).exists():
#             print(f"Tax group already exist with name {name}")
#             continue
#         tax_group = TaxGroup.objects.create(name=name)
#         for tax in taxes:
#             tax_map, _ = GroupTaxMapping.objects.update_or_create(tax_group=tax_group, tax=tax)
#             print(f"Tax Group Mapping created {_} | instance {tax_map}")
#
#     print('create_tax_groups | ENDED')
#
#
#
