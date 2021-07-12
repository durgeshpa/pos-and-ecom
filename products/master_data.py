import logging
import io
import datetime
import csv

from django.db.models import Q
from brand.models import Brand
from categories.models import Category
from products.models import Product, ParentProduct, ParentProductTaxMapping, ProductHSN, ParentProductCategory, Tax, \
    Repackaging, DestinationRepackagingCostMapping, ProductTaxMapping, ProductSourceMapping, ProductPackingMapping

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class SetMasterData(object):
    """
    It will call the functions mentioned in UploadMasterData class as per the condition of header_list
    """

    @classmethod
    def set_master_data(cls, excel_file_data_list):
        UploadMasterData.set_inactive_status(excel_file_data_list)
        UploadMasterData.set_parent_data(excel_file_data_list)
        UploadMasterData.set_child_parent(excel_file_data_list)
        UploadMasterData.set_sub_brand_and_brand(excel_file_data_list)
        UploadMasterData.set_sub_category_and_category(excel_file_data_list)
        UploadMasterData.set_child_data(excel_file_data_list)


class UploadMasterData(object):
    """
    This function will be used for following operations:
    a)Set the Status to "Deactivated" for a Product
    b)Mapping of "Sub Brand" to "Brand"
    c)Mapping of "Sub Category" to "Category"
    d)Set the data for "Parent SKU"
    e)Mapping of Child SKU to Parent SKU
    f)Set the Child SKU Data
    """

    @classmethod
    def set_inactive_status(cls, csv_file_data_list):
        try:
            count = 0
            info_logger.info("Method Start to set Inactive status from excel file")
            child_product = Product.objects.all()
            for row in csv_file_data_list:
                if row['status'] == 'deactivated':
                    count += 1
                    product = child_product.filter(product_sku=row['sku_id'])
                    if 'mrp' in row.keys() and not row['mrp'] == '':
                        product.update(status='deactivated', product_mrp=row['mrp'])
                    else:
                        product.update(status='deactivated')
                else:
                    continue
            info_logger.info("Set Inactive Status function called -> Inactive row id count :" + str(count))
            info_logger.info("Method Complete to set the Inactive status from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Inactive Status Functionality' + {str(e)}")

    @classmethod
    def set_sub_brand_and_brand(cls, csv_file_data_list):
        """
            Updating Brand & Sub Brand
        """
        try:
            count = 0
            row_num = 1
            sub_brand = []
            info_logger.info('Method Start to set the Sub-brand to Brand mapping from excel file')
            brand = Brand.objects.all()
            for row in csv_file_data_list:
                count += 1
                row_num += 1
                try:
                    if 'sub_brand_id' in row.keys() and not row['sub_brand_id'] == '':
                        if row['sub_brand_id'] == row['brand_id']:
                            continue
                        else:
                            brand.filter(id=row['sub_brand_id']).update(brand_parent=row['brand_id'])
                except:
                    sub_brand.append(str(row_num))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Sub brand is not updated in these row :" + str(sub_brand))
            info_logger.info("Method complete to set the Sub-Brand to Brand mapping from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with 'Set Sub Brand and Brand Functionality'"
                              f" + {str(e)}")

    @classmethod
    def set_sub_category_and_category(cls, csv_file_data_list):
        try:
            count = 0
            row_num = 1
            sub_category = []
            info_logger.info("Method Start to set the Sub-Category to Category mapping from excel file")
            category = Category.objects.all()
            for row in csv_file_data_list:
                count += 1
                row_num += 1
                try:
                    if 'sub_category_id' in row.keys() and not row['sub_category_id'] == '':
                        if row['sub_category_id'] == row['category_id']:
                            continue
                        else:
                            category.filter(id=row['sub_category_id']).update(category_parent=row['category_id'])
                except:
                    sub_category.append(str(row_num))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Sub Category is not updated in these row :" + str(sub_category))
            info_logger.info("Method Complete to set the Sub-Category to Category mapping from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Sub Category and Category Functionality' + {str(e)}")

    @classmethod
    def set_parent_data(cls, csv_file_data_list):
        try:
            count = 0
            row_num = 1
            parent_data = []
            info_logger.info("Method Start to set the data for Parent SKU")
            parent_pro = ParentProduct.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                if not row['status'] == 'deactivated':
                    count += 1
                    try:
                        parent_product = parent_pro.filter(parent_id=row['parent_id'])

                        fields = ['product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)',
                                  'tax_3(surcharge)', 'brand_case_size', 'inner_case_size', 'brand_id',
                                  'sub_brand_id', 'category_id', 'sub_category_id', 'is_ptr_applicable', 'ptr_type',
                                  'ptr_percent', 'is_ars_applicable', 'max_inventory_in_days',
                                  'is_lead_time_applicable']

                        available_fields = []
                        for col in fields:
                            if col in row.keys():
                                if row[col] != '':
                                    available_fields.append(col)

                        for col in available_fields:

                            if col == 'product_type':
                                parent_product.update(product_type=row['product_type'])

                            if col == 'hsn':
                                parent_product.update(
                                    product_hsn=ProductHSN.objects.filter(product_hsn_code=row['hsn']).last())

                            if col == 'tax_1(gst)':
                                tax = Tax.objects.filter(tax_name=row['tax_1(gst)'])
                                ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id,
                                                                       tax__tax_type='gst').update(tax=tax[0])
                                if 'sku_id' in row.keys() and row['sku_id'] != '':
                                    product = Product.objects.filter(product_sku=row['sku_id'])
                                    ProductTaxMapping.objects.filter(product=product[0].id, tax__tax_type='gst'). \
                                        update(tax=tax[0])

                            if col == 'tax_2(cess)':
                                tax = Tax.objects.filter(tax_name=row['tax_2(cess)'])
                                ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id,
                                                                       tax__tax_type='cess').update(tax=tax[0])
                                if 'sku_id' in row.keys() and row['sku_id'] != '':
                                    product = Product.objects.filter(product_sku=row['sku_id'])
                                    ProductTaxMapping.objects.filter(product=product[0].id, tax__tax_type='cess'). \
                                        update(tax=tax[0])

                            if col == 'tax_3(surcharge)':
                                tax = Tax.objects.filter(tax_name=row['tax_3(surcharge)'])
                                ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id,
                                                                       tax__tax_type='surcharge').update(
                                    tax=tax[0])
                                if 'sku_id' in row.keys() and row['sku_id'] != '':
                                    product = Product.objects.filter(product_sku=row['sku_id'])
                                    ProductTaxMapping.objects.filter(product=product[0].id, tax__tax_type='surcharge'). \
                                        update(tax=tax[0])

                            if col == 'inner_case_size':
                                parent_pro.filter(parent_id=row['parent_id']).update \
                                    (inner_case_size=row['inner_case_size'])

                            if col == 'sub_category_id':
                                if row['sub_category_id'] == row['category_id']:
                                    continue
                                else:
                                    ParentProductCategory.objects.filter(parent_product=parent_product[0].id).update(
                                        category=Category.objects.filter(id=row['sub_category_id']).last())

                            if col == 'sub_brand_id':
                                parent_pro.filter(parent_id=row['parent_id']).update(
                                    parent_brand=Brand.objects.filter(id=row['sub_brand_id']).last())

                            if col == 'is_ptr_applicable':
                                parent_pro.filter(parent_id=row['parent_id']).update \
                                    (is_ptr_applicable=True if row['is_ptr_applicable'].lower() == 'yes' else False)

                            if col == 'ptr_type':
                                parent_pro.filter(parent_id=row['parent_id']).update \
                                    (ptr_type=None if not row['is_ptr_applicable'].lower() == 'yes' else ParentProduct.PTR_TYPE_CHOICES.MARK_UP
                                    if row[
                                           'ptr_type'].lower() == 'mark up' else ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN)

                            if col == 'ptr_percent':
                                parent_pro.filter(parent_id=row['parent_id']).update \
                                    (ptr_percent=None if not row['is_ptr_applicable'].lower() == 'yes' else row[
                                        'ptr_percent'])

                            if col == 'is_ars_applicable':
                                parent_pro.filter(parent_id=row['parent_id']).update \
                                    (is_ars_applicable=True if row['is_ars_applicable'].lower() == 'yes' else False)

                            if col == 'max_inventory_in_days':
                                parent_pro.filter(parent_id=row['parent_id']).update \
                                    (max_inventory=row['max_inventory_in_days'])

                            if col == 'is_lead_time_applicable':
                                parent_pro.filter(parent_id=row['parent_id']).update \
                                    (is_lead_time_applicable=True if row[
                                                                         'is_lead_time_applicable'].lower() == 'yes' else False)

                    except Exception as e:
                        parent_data.append(str(row_num) + ' ' + str(e))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info(
                "Some Error Found in these rows, while working with Parent Data Functionality :" + str(parent_data))
            info_logger.info("Method Complete to set the data for Parent SKU")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Parent Data Functionality' + {str(e)}")

    @classmethod
    def set_child_parent(cls, csv_file_data_list):
        try:
            info_logger.info("Method Start to set the Child to Parent mapping from excel file")
            count = 0
            row_num = 1
            set_child = []
            child_product = Product.objects.all()
            parent_product = ParentProduct.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                if not row['status'] == 'deactivated':
                    count += 1
                    try:
                        child_pro = child_product.filter(product_sku=row['sku_id'])
                        parent_pro = parent_product.filter(parent_id=row['parent_id']).last()
                        child_pro.update(parent_product=parent_pro)
                    except:
                        set_child.append(str(row_num))

            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Child SKU is not exist in these row :" + str(set_child))
            info_logger.info("Method complete to set the Child to Parent mapping from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Child Parent Functionality' + {str(e)}")

    @classmethod
    def set_child_data(cls, csv_file_data_list):
        try:
            info_logger.info("Method Start to set the Child data from excel file")
            count = 0
            row_num = 1
            child_data = []
            product = Product.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                count += 1
                try:
                    child_product = product.filter(product_sku=row['sku_id'])
                    child_product.update(product_name=row['sku_name'], status=row['status'])
                    fields = ['ean', 'mrp', 'weight_unit', 'weight_value']
                    available_fields = []
                    for col in fields:
                        if col in row.keys() and row[col] != '':
                            available_fields.append(col)

                    for col in available_fields:
                        if col == 'ean':
                            child_product.update(product_ean_code=row['ean'])
                        if col == 'mrp':
                            child_product.update(product_mrp=row['mrp'])
                        if col == 'weight_value':
                            child_product.update(weight_value=row['weight_value'])

                    if 'repackaging_type' in row.keys() and row['repackaging_type'] == 'destination':
                        DestinationRepackagingCostMapping.objects.filter(destination=child_product[0].id) \
                            .update(raw_material=row['raw_material'],
                                    wastage=row['wastage'],
                                    fumigation=row['fumigation'],
                                    label_printing=row['label_printing'],
                                    packing_labour=row['packing_labour'],
                                    primary_pm_cost=row['primary_pm_cost'],
                                    secondary_pm_cost=row['secondary_pm_cost'],
                                    final_fg_cost=row['final_fg_cost'],
                                    conversion_cost=row['conversion_cost'])
                except Exception as e:
                    child_data.append(str(row_num) + ' ' + str(e))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info(
                "Some error found in these row while working with Child data Functionality:" + str(child_data))
            info_logger.info("Script Complete to set the Child data")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Child Data Functionality' + {str(e)}")

    @classmethod
    def set_product_tax(cls, csv_file_data_list):
        """
            Updating Parent Product & Tax
        """
        try:
            info_logger.info('Method Start to update the Parent Product with Tax')
            for row in csv_file_data_list:
                parent_pro_id = ParentProduct.objects.filter(parent_id=row['parent_id'].strip()).last()
                queryset = ParentProductTaxMapping.objects.filter(parent_product=parent_pro_id)
                if queryset.exists():
                    gst_tax = Tax.objects.get(tax_type='gst', tax_percentage=float(row['gst']))
                    queryset.filter(tax__tax_type='gst').update(tax=gst_tax)
                    if row['cess']:
                        cess_tax = Tax.objects.get(tax_type='cess', tax_percentage=float(row['cess']))
                        product_cess_tax = queryset.filter(tax__tax_type='cess')
                        if product_cess_tax.exists():
                            queryset.filter(tax__tax_type='cess').update(tax_id=cess_tax)
                        else:
                            ParentProductTaxMapping.objects.create(parent_product=parent_pro_id, tax=cess_tax)
                    if row['surcharge']:
                        surcharge_tax = Tax.objects.get(tax_type='surcharge', tax_percentage=float(row['surcharge']))
                        product_surcharge_tax = queryset.filter(tax__tax_type='surcharge')
                        if product_surcharge_tax.exists():
                            queryset.filter(tax__tax_type='surcharge').update(tax_id=surcharge_tax)
                        else:
                            ParentProductTaxMapping.objects.create(parent_product=parent_pro_id, tax=surcharge_tax)

            info_logger.info("Method complete to update the Parent Product with Tax from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with update Parent Product with Tax Functionality'"
                              f" + {str(e)}")

    @classmethod
    def create_bulk_parent_product(cls, csv_file_data_list, user):
        """
            Create Parent Product
        """
        try:
            info_logger.info('Method Start to create Parent Product')
            for row in csv_file_data_list:
                parent_product = ParentProduct.objects.create(
                    name=row['name'].strip(),
                    parent_brand=Brand.objects.filter(brand_name=row['brand_name'].strip()).last(),
                    product_hsn=ProductHSN.objects.filter(product_hsn_code=row['hsn'].replace("'", '')).last(),
                    inner_case_size=int(row['inner_case_size']), product_type=row['product_type'],
                    is_ptr_applicable=(True if row['is_ptr_applicable'].lower() == 'yes' else False),
                    ptr_type=(None if not row['is_ptr_applicable'].lower() == 'yes' else ParentProduct.PTR_TYPE_CHOICES.MARK_UP
                    if row['ptr_type'].lower() == 'mark up' else ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN),
                    ptr_percent=(None if not row['is_ptr_applicable'].lower() == 'yes' else row['ptr_percent']),
                    is_ars_applicable=True if row['is_ars_applicable'].lower() == 'yes' else False,
                    max_inventory=row['max_inventory_in_days'].lower(),
                    is_lead_time_applicable=(True if row['is_lead_time_applicable'].lower() == 'yes' else False),
                    created_by=user
                )

                parent_gst = int(row['gst'])
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='gst', tax_percentage=parent_gst).last())

                parent_cess = int(row['cess']) if row['cess'] else 0
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='cess', tax_percentage=parent_cess).last())

                parent_surcharge = float(row['surcharge']) if row['surcharge'] else 0
                if Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).exists():
                    ParentProductTaxMapping.objects.create(
                        parent_product=parent_product,
                        tax=Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).last())
                else:
                    new_surcharge_tax = Tax.objects.create(tax_name='Surcharge - {}'.format(parent_surcharge),
                                                           tax_type='surcharge',
                                                           tax_percentage=parent_surcharge,
                                                           tax_start_at=datetime.datetime.now())

                    ParentProductTaxMapping.objects.create(parent_product=parent_product, tax=new_surcharge_tax)

                if Category.objects.filter(category_name=row['category_name'].strip()).exists():
                    ParentProductCategory.objects.create(
                        parent_product=parent_product,
                        category=Category.objects.filter(category_name=row['category_name'].strip()).last())

                else:
                    categories = row['category_name'].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        ParentProductCategory.objects.create(parent_product=parent_product,
                                                             category=Category.objects.filter(
                                                                 category_name=cat).last())

            info_logger.info("Method complete to create the Parent Product from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with create Parent Product "
                              f" + {str(e)}")

    @classmethod
    def create_bulk_child_product(cls, csv_file_data_list, user):
        """
            Create Child Product
        """
        try:
            info_logger.info('Method Start to create Child Product')
            for row in csv_file_data_list:
                child_product = Product.objects.create(
                    parent_product=ParentProduct.objects.filter(parent_id=row['parent_id']).last(),
                    reason_for_child_sku=(row['reason_for_child_sku'].lower()), product_name=row['name'],
                    product_ean_code=row['ean'].replace("'", ''), product_mrp=float(row['mrp']),
                    weight_value=float(row['weight_value']), weight_unit= str(row['weight_unit'].lower()),
                    repackaging_type=row['repackaging_type'], created_by=user)

                if row['repackaging_type'] == 'destination':
                    source_map = []
                    for product_skus in row['source_sku_id'].split(','):
                        pro = product_skus.strip()
                        if pro is not '' and pro not in source_map and \
                                Product.objects.filter(product_sku=pro, repackaging_type='source').exists():
                            source_map.append(pro)
                    for sku in source_map:
                        pro_sku = Product.objects.filter(product_sku=sku, repackaging_type='source').last()
                        ProductSourceMapping.objects.create(destination_sku=child_product, source_sku=pro_sku,
                                                            status=True)
                    DestinationRepackagingCostMapping.objects.create(destination=child_product,
                                                                     raw_material=float(row['raw_material']),
                                                                     wastage=float(row['wastage']),
                                                                     fumigation=float(row['fumigation']),
                                                                     label_printing=float(row['label_printing']),
                                                                     packing_labour=float(row['packing_labour']),
                                                                     primary_pm_cost=float(row['primary_pm_cost']),
                                                                     secondary_pm_cost=float(row['secondary_pm_cost']))
                    ProductPackingMapping.objects.create(sku=child_product, packing_sku=Product.objects.get(product_sku=row['packing_sku_id']),
                                                         packing_sku_weight_per_unit_sku=float(row['packing_material_weight']))

            info_logger.info("Method complete to create the Child Product from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with create Child Product "
                              f" + {str(e)}")

    @classmethod
    def create_bulk_category(cls, csv_file_data_list, user):
        """
            Create Category
        """
        try:
            info_logger.info('Method Start to create Category')
            for row in csv_file_data_list:
                Category.objects.create(
                    category_name=row['name'],
                    category_slug=row['category_slug'],
                    category_parent=Category.objects.get(category_name=row['category_parent'].strip()),
                    category_desc=row['category_desc'],
                    category_sku_part=row['category_sku_part'],
                    created_by=user)

            info_logger.info("Method complete to create Category from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with create Category "
                              f" + {str(e)}")

    @classmethod
    def create_bulk_brand(cls, csv_file_data_list, user):
        """
            Create Brand
        """
        try:
            info_logger.info('Method Start to create Brand')

            for row in csv_file_data_list:
                Brand.objects.create(
                    brand_name=row['name'],
                    brand_slug=row['brand_slug'],
                    brand_parent=Brand.objects.get(brand_name=row['brand_parent'].strip()),
                    brand_description=row['brand_description'],
                    brand_code=row['brand_code'],
                    created_by=user)

            info_logger.info("Method complete to create Brand from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with create Brand "
                              f" + {str(e)}")


class DownloadMasterData(object):
    """
        This function will be used for following operations:
        a)return an Sample File in xlsx format which can be used for uploading the master_data
        b)return an Sample File in xlsx format which can be used for Status to "Deactivated" for a Product
        c)return an Sample File in xlsx format which can be used for Mapping of "Sub Brand" to "Brand"
        d)return an Sample File in xlsx format which can be used for Mapping of "Sub Category" to "Category"
        e)return an Sample File in xlsx format which can be used for Set the data for "Parent SKU"
        f)return an Sample File in xlsx format which can be used for Mapping of Child SKU to Parent SKU
        g)return an Sample File in xlsx format which can be used for Set the Child SKU Data
        """

    def response_workbook(filename):

        csv_file_buffer = io.StringIO()
        date = datetime.datetime.now().strftime('%d_%b_%y_%I_%M')
        writer = csv.writer(csv_file_buffer, dialect='excel', delimiter=',')
        csv_filename = f'{date}-{filename}'
        return csv_file_buffer, writer, csv_filename

    @classmethod
    def set_inactive_status_sample_file(cls, validated_data):

        response, writer, csv_filename = DownloadMasterData.response_workbook("active_inactive_status_sample")
        columns = ['sku_id', 'sku_name', 'mrp', 'status', ]
        writer.writerow(columns)

        products = Product.objects.values('product_sku', 'product_name', 'product_mrp', 'status', ). \
            filter(Q(parent_product__parent_product_pro_category__category__category_name__icontains=
                     validated_data['category_id'].category_name))

        for product in products:
            row=[]
            row.append(product['product_sku'])
            row.append(product['product_name'])
            row.append(product['product_mrp'])
            row.append(product['status'])

            writer.writerow(row)

        info_logger.info("Set Inactive Status Sample File has been Successfully Downloaded")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def brand_sub_brand_mapping_sample_file(cls):
        response, writer, csv_filename = DownloadMasterData.response_workbook("active_inactive_status_sample")
        columns = ['brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name', ]
        writer.writerow(columns)

        brands = Brand.objects.values('id', 'brand_name', 'brand_parent_id', 'brand_parent__brand_name')
        for brand in brands:
            row = []
            if brand['brand_parent_id']:
                row.append(brand['brand_parent_id'])
                row.append(brand['brand_parent__brand_name'])
                row.append(brand['id'])
                row.append(brand['brand_name'])

            else:
                row.append(brand['id'])
                row.append(brand['brand_name'])
                row.append(brand['brand_parent_id'])
                row.append(brand['brand_parent__brand_name'])

            writer.writerow(row)

        info_logger.info("Brand and Sub Brand Mapping Sample File has been Successfully Downloaded")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def category_sub_category_mapping_sample_file(cls):

        response, writer, csv_filename = DownloadMasterData.response_workbook("subCategory-CategorySample")
        columns = ['category_id', 'category_name', 'sub_category_id', 'sub_category_name', ]
        writer.writerow(columns)

        categories = Category.objects.values('id', 'category_name', 'category_parent_id',
                                             'category_parent__category_name')
        for category in categories:
            row = []
            if category['category_parent_id']:
                row.append(category['category_parent_id'])
                row.append(category['category_parent__category_name'])
                row.append(category['id'])
                row.append(category['category_name'])
            else:
                row.append(category['id'])
                row.append(category['category_name'])
                row.append(category['category_parent_id'])
                row.append(category['category_parent__category_name'])

            writer.writerow(row)
        info_logger.info("Category and Sub Category Mapping Sample File has been Successfully Downloaded")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_child_with_parent_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("child_parent_mapping_data_sample")
        columns = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'status', ]
        writer.writerow(columns)

        products = Product.objects.values('product_sku', 'product_name',
                                          'parent_product__parent_id', 'parent_product__name', 'status') \
            .filter(Q(parent_product__parent_product_pro_category__category__category_name__icontains=validated_data[
            'category_id'].category_name))

        for product in products:
            row = []
            row.append(product['product_sku'])
            row.append(product['product_name'])
            row.append(product['parent_product__parent_id'])
            row.append(product['parent_product__name'])
            row.append(product['status'])

            writer.writerow(row)

        info_logger.info("Child Parent Mapping Sample File has been Successfully Downloaded")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_child_data_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("child_data_sample")
        columns = ['sku_id', 'sku_name', 'ean', 'mrp', 'weight_unit', 'weight_value', 'status',
                   'repackaging_type', 'source_sku_id', 'source_sku_name', 'raw_material', 'wastage',
                   'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost',
                   'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']
        writer.writerow(columns)

        products = Product.objects.values('id', 'product_sku', 'product_name', 'product_ean_code', 'product_mrp',
                                          'weight_unit', 'weight_value', 'status', 'repackaging_type', ) \
            .filter(Q(parent_product__parent_product_pro_category__category__category_name__icontains=validated_data['category_id'].category_name))

        for product in products:
            row = []
            row.append(product['product_sku'])
            row.append(product['product_name'])
            row.append(product['product_ean_code'])
            row.append(product['product_mrp'])
            row.append(product['weight_unit'])
            row.append(product['weight_value'])
            row.append(product['status'])
            row.append(product['repackaging_type'])
            source_sku_name = Repackaging.objects.select_related('source_sku').filter(destination_sku=product['id'])
            source_sku_ids = []
            source_sku_names = []
            for sourceSKU in source_sku_name:
                if sourceSKU.source_sku.product_sku not in source_sku_ids:
                    source_sku_ids.append(sourceSKU.source_sku.product_sku)
                if sourceSKU.source_sku.product_name not in source_sku_names:
                    source_sku_names.append(sourceSKU.source_sku.product_name)
            if source_sku_ids:
                row.append(str(source_sku_ids))
            else:
                row.append('')
            if source_sku_names:
                row.append(str(source_sku_names))
            else:
                row.append('')
            costs = DestinationRepackagingCostMapping.objects.values('raw_material', 'wastage', 'fumigation',
                                                                     'label_printing', 'packing_labour',
                                                                     'primary_pm_cost', 'secondary_pm_cost',
                                                                     'final_fg_cost',
                                                                     'conversion_cost').filter(destination=product['id'])
            for cost in costs:
                row.append(cost['raw_material'])
                row.append(cost['wastage'])
                row.append(cost['fumigation'])
                row.append(cost['label_printing'])
                row.append(cost['packing_labour'])
                row.append(cost['primary_pm_cost'])
                row.append(cost['secondary_pm_cost'])
                row.append(cost['final_fg_cost'])
                row.append(cost['conversion_cost'])

            writer.writerow(row)

        info_logger.info("Child Data Sample File has been Successfully Downloaded")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_parent_data_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("parent_data_sample")
        columns = ['parent_id', 'parent_name', 'product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)', 'tax_3(surcharge)',
                   'inner_case_size', 'brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name', 'category_id',
                   'category_name', 'sub_category_id', 'sub_category_name', 'status', 'is_ptr_applicable', 'ptr_type',
                   'ptr_percent', 'is_ars_applicable', 'max_inventory_in_days', 'is_lead_time_applicable']
        writer.writerow(columns)

        parent_products = ParentProductCategory.objects.values('parent_product__id', 'parent_product__parent_id',
                                                               'parent_product__name', 'parent_product__product_type',
                                                               'parent_product__product_hsn__product_hsn_code',
                                                               'parent_product__inner_case_size',
                                                               'parent_product__parent_brand__id',
                                                               'parent_product__parent_brand__brand_name',
                                                               'parent_product__parent_brand__brand_parent_id',
                                                               'parent_product__parent_brand__brand_parent__brand_name',
                                                               'category__id', 'category__category_name',
                                                               'category__category_parent_id',
                                                               'category__category_parent__category_name',
                                                               'parent_product__status',
                                                               'parent_product__is_ptr_applicable',
                                                               'parent_product__ptr_type',
                                                               'parent_product__ptr_percent',
                                                               'parent_product__is_ars_applicable',
                                                               'parent_product__max_inventory',
                                                               'parent_product__is_lead_time_applicable').filter(
            category=validated_data['category_id'])
        for product in parent_products:
            row = []
            tax_list = ['', '', '']
            row.append(product['parent_product__parent_id'])
            row.append(product['parent_product__name'])
            row.append(product['parent_product__product_type'])
            row.append(product['parent_product__product_hsn__product_hsn_code'])
            taxes = ParentProductTaxMapping.objects.select_related('tax').filter(
                parent_product=product['parent_product__id'])
            for tax in taxes:
                if tax.tax.tax_type == 'gst':
                    tax_list[0] = tax.tax.tax_name
                if tax.tax.tax_type == 'cess':
                    tax_list[1] = tax.tax.tax_name
                if tax.tax.tax_type == 'surcharge':
                    tax_list[2] = tax.tax.tax_name
            row.extend(tax_list)
            row.append(product['parent_product__inner_case_size'])

            if product['parent_product__parent_brand__brand_parent_id']:
                row.append(product['parent_product__parent_brand__brand_parent_id'])
                row.append(product['parent_product__parent_brand__brand_parent__brand_name'])
                row.append(product['parent_product__parent_brand__id'])
                row.append(product['parent_product__parent_brand__brand_name'])
            else:
                row.append(product['parent_product__parent_brand__id'])
                row.append(product['parent_product__parent_brand__brand_name'])
                row.append(product['parent_product__parent_brand__brand_parent_id'])
                row.append(product['parent_product__parent_brand__brand_parent__brand_name'])

            if product['category__category_parent_id']:
                row.append(product['category__category_parent_id'])
                row.append(product['category__category_parent__category_name'])
                row.append(product['category__id'])
                row.append(product['category__category_name'])
            else:
                row.append(product['category__id'])
                row.append(product['category__category_name'])
                row.append(product['category__category_parent_id'])
                row.append(product['category__category_parent__category_name'])

            if type(product['parent_product__status']):
                row.append("active")
            else:
                row.append("deactivated")
            row.append('Yes' if product['parent_product__is_ptr_applicable'] else 'No')
            row.append(get_ptr_type_text(product['parent_product__ptr_type']))
            row.append(product['parent_product__ptr_percent'])
            row.append('Yes' if product['parent_product__is_ars_applicable'] else 'No')
            row.append(product['parent_product__max_inventory'])
            row.append('Yes' if product['parent_product__is_lead_time_applicable'] else 'No')

            writer.writerow(row)
        info_logger.info("Parent Data Sample File has been Successfully Downloaded")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_product_tax_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("bulk_product_tax_gst_update_sample")
        columns = ['parent_id', 'gst', 'cess', 'surcharge', ]
        writer.writerow(columns)

        writer.writerow(['PHEATOY0006', 2, 12, 4])

        info_logger.info("bulk tax update Sample CSVExported successfully ")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_parent_product_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("bulk_parent_product_create_sample")
        columns = ["name", "brand_name", "category_name", "hsn", "gst", "cess", "surcharge", "inner_case_size",
                   "product_type", "is_ptr_applicable", "ptr_type", "ptr_percent", "is_ars_applicable",
                   "max_inventory_in_days", "is_lead_time_applicable"]
        writer.writerow(columns)
        data = [["parent1", "Too Yumm", "Health Care, Beverages, Grocery & Staples", "123456", "18", "12", "100",
                 "10", "b2b", "yes", "Mark Up", "12", "yes", "2", "yes"],
                ["parent2", "Too Yumm", "Grocery & Staples", "123456", "18", "0", "100", "10", "b2c", "no",
                 " ", "", "no", "2", "yes"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Parent Product Sample CSVExported successfully ")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_child_product_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("bulk_child_product_create_sample")
        writer = csv.writer(response)
        writer.writerow(["parent_id", "reason_for_child_sku", "name", "ean",
                         "mrp", "weight_value", "weight_unit", "repackaging_type", "source_sku_id",
                         'raw_material', 'wastage', 'fumigation', 'label_printing',
                         'packing_labour', 'primary_pm_cost', 'secondary_pm_cost', "packing_sku_id",
                         "packing_material_weight"])
        data = [["PHEAMGI0001", "Default", "TestChild1", "abcdefgh", "50", "20", "Gram", "none"],
                ["PHEAMGI0001", "Default", "TestChild2", "abcdefgh", "50", "20", "Gram", "source"],
                ["PHEAMGI0001", "Default", "TestChild3", "abcdefgh", "50", "20", "Gram", "destination",
                 "SNGSNGGMF00000016, SNGSNGGMF00000016", "10.22", "2.33", "7", "4.33", "5.33", "10.22", "5.22",
                 "BPOBLKREG00000001", "10.00"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Child Product Sample CSVExported successfully ")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_brand_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("bulk_brand_create_sample")
        columns = ["name", "brand_slug", "brand_parent", "brand_description", "brand_code"]
        writer.writerow(columns)

        data = [["NatureLand", "natureland", "Dermanest", "", "NAT"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Brand Sample CSVExported successfully ")

        info_logger.info("bulk tax update Sample CSVExported successfully ")
        response.seek(0)
        return response, csv_filename

    @classmethod
    def set_category_sample_file(cls, validated_data):
        response, writer, csv_filename = DownloadMasterData.response_workbook("bulk_category_create_sample")
        columns = ["name", "category_slug", "category_desc", "category_parent", "category_sku_part" ]
        writer.writerow(columns)
        data = [["Home Improvement", "home_improvement", "XYZ", "Processed Food", "HMI"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Category Sample CSVExported successfully ")
        response.seek(0)
        return response, csv_filename


def get_ptr_type_text(ptr_type=None):
    if ptr_type is not None and ptr_type in ParentProduct.PTR_TYPE_CHOICES:
        return ParentProduct.PTR_TYPE_CHOICES[ptr_type]
    return ''
