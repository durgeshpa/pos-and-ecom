import csv
import datetime
import re
import codecs
import json


from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import ParentProduct, ParentProductCategory, Product, Tax, ProductPrice
from products.models import ParentProductTaxMapping, ProductTaxMapping, ProductHSN
from products.forms import UploadParentProductAdminForm
from brand.models import Brand
from categories.models import Category


class Command(BaseCommand):
    help = 'Migration script for Parent Child Data'

    def handle(self, *args, **options):
        create_parents()
        update_child_products()


def create_parents():
    skip_ids = []
    cig_ids = []
    parent_data = open('products/management/commands/parent_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(parent_data, 'utf-8'))
    first_row = next(reader)
    for row_id, row in enumerate(reader):
        if 'cigarette' in row[2].lower():
            cig_ids.append(row_id)
            continue
        valid, empty = validate_parent_row(row_id, row)
        if not valid:
            if empty:
                continue
            print("row {} with data {}".format(row_id, row))
            skip_ids.append(row_id)
            continue
        create_parent_product(row_id, row)
    print(skip_ids)
    print(len(skip_ids))
    print(cig_ids)
    print(len(cig_ids))

def validate_parent_row(row_id, row):
    if len(row) == 0:
        return True, True
    if '' in row:
        if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
            row[5] == '' and row[6] == '' and row[7] == '' and row[8] == ''):
            return True, True
    if not row[0]:
        print('Empty name at row {}'.format(row_id))
        return False, False
    elif not re.match("^[ \w\$\_\,\%\@\.\'\/\#\&\+\=\`\-\(\)\*\!\:]*$", row[0].replace('\\', '')):
        print('Wrong format name at row {}'.format(row_id))
        return False, False
    if not row[1]:
        print('Empty brand at row {}'.format(row_id))
        return False, False
    elif not Brand.objects.filter(brand_name=row[1]).exists():
        print('brand not found at row {}'.format(row_id))
        return False, False
    if not row[2]:
        print('Empty category at row {}'.format(row_id))
        return False, False
    else:
        if not Category.objects.filter(Q(category_slug=row[2]) | Q(category_name=row[2])).exists():
            categories = row[2].split(',')
            for cat in categories:
                if not Category.objects.filter(Q(category_slug=cat.strip()) | Q(category_name=cat.strip())).exists():
                    print('Cat not found at row {}'.format(row_id))
                    return False, False
    if not row[3]:
        print('Empty HSN at row {}'.format(row_id))
        return False, False
    elif not ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).exists():
        if not ProductHSN.objects.filter(product_hsn_code=('0' + row[3].replace("'", ''))).exists():
            print('hsn not found at row {}'.format(row_id))
            ProductHSN.objects.create(product_hsn_code=row[3].replace("'", '')).save()
            # return False, False
    if not row[4]:
        print('Empty GST at row {}'.format(row_id))
        return False, False
    elif not re.match("^([0]|[5]|[1][2]|[1][8]|[2][8])(\s+)?(%)?$", row[4]):
        print('invalid gst at row {}'.format(row_id))
        return False, False
    if row[5] and not re.match("^([0]|[1][2])(\s+)?%?$", row[5]):
        print('invalid cess at row {}'.format(row_id))
        return False, False
    # if row[6] and not re.match("^[0-9]\d*(\.\d{1,2})?(\s+)?%?$", row[6]):
    if row[6] and not re.match("[0](\s+)?$", row[6]):
        print('invalid surcharge at row {}'.format(row_id))
        return False, False
    if not row[7]:
        print('missing bcs at row {}'.format(row_id))
        return False, False
    elif not re.match("^\d+$", row[7]):
        print('invalid bcs at row {}'.format(row_id))
        return False, False
    if not row[8]:
        print('missing ics at row {}'.format(row_id))
        return False, False
    elif not re.match("^\d+$", row[8]):
        print('invalid bcs at row {}'.format(row_id))
        return False, False
    return True, False

def gst_mapper(gst):
    if '0' in gst:
        return 0
    if '5' in gst:
        return 5
    if '12' in gst:
        return 12
    if '18' in gst:
        return 18
    if '28' in gst:
        return 28

def cess_mapper(cess):
    if '0' in cess:
        return 0
    if '12' in cess:
        return 12

def create_parent_product(row_id, row):
    if ParentProduct.objects.filter(name=row[0].strip().replace('\\', '')).exists():
        # parent = ParentProduct.objects.filter(name=row[0].strip().replace('\\', '')).last()
        # print('Parent Product already exists for row {} with name {} with Parent ID {}'.format(row_id, row[0].strip().replace('\\', ''), parent.id))
        return
    if ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).exists():
        hsn_entry = ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).last()
    else:
        hsn_entry = ProductHSN.objects.filter(product_hsn_code=('0' + row[3].replace("'", ''))).last()
    parent_product = ParentProduct.objects.create(
        name=row[0].strip().replace('\\', ''),
        parent_brand=Brand.objects.filter(brand_name=row[1]).last(),
        product_hsn=hsn_entry,
        brand_case_size=int(row[7]),
        inner_case_size=int(row[8]),
        product_type='both' # Need to confirm
    )
    parent_product.save()
    parent_gst = gst_mapper(row[4])
    ParentProductTaxMapping.objects.create(
        parent_product=parent_product,
        tax=Tax.objects.filter(tax_type='gst', tax_percentage=parent_gst).last()
    ).save()
    parent_cess = cess_mapper(row[5]) if row[5] else 0
    ParentProductTaxMapping.objects.create(
        parent_product=parent_product,
        tax=Tax.objects.filter(tax_type='cess', tax_percentage=parent_cess).last()
    ).save()
    parent_surcharge = float(row[6]) if row[6] else 0
    if Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).exists():
        ParentProductTaxMapping.objects.create(
            parent_product=parent_product,
            tax=Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).last()
        ).save()
    else:
        new_surcharge_tax = Tax.objects.create(
            tax_name='Surcharge - {}'.format(parent_surcharge),
            tax_type='surcharge',
            tax_percentage=parent_surcharge,
            tax_start_at=datetime.datetime.now()
        )
        new_surcharge_tax.save()
        ParentProductTaxMapping.objects.create(
            parent_product=parent_product,
            tax=new_surcharge_tax
        ).save()
    if Category.objects.filter(Q(category_slug=row[2]) | Q(category_name=row[2])).exists():
        parent_product_category = ParentProductCategory.objects.create(
            parent_product=parent_product,
            category=Category.objects.filter(Q(category_slug=row[2]) | Q(category_name=row[2])).last()
        )
        parent_product_category.save()
    else:
        categories = row[2].split(',')
        for cat in categories:
            cat = cat.strip()
            parent_product_category = ParentProductCategory.objects.create(
                parent_product=parent_product,
                category=Category.objects.filter(Q(category_slug=cat) | Q(category_name=cat)).last()
            )
            parent_product_category.save()

def update_child_products():
    count = 0
    status_file = open("products/management/commands/product_status_data.txt", "r")
    status_data = json.loads(status_file.read())
    print("status")
    print(len(status_data))
    status_file.close()
    mrp_file = open("products/management/commands/product_mrp_data.txt", "r")
    mrp_data = json.loads(mrp_file.read())
    print("mrp")
    print(len(mrp_data))
    mrp_file.close()
    mapping_file = open('products/management/commands/parent_child_mapping.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(mapping_file, 'utf-8'))
    first_row = next(reader)
    not_found = []
    parent_nf = []
    for row_id, row in enumerate(reader):
        if len(row) == 0:
            continue
        if '' in row:
            if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == ''):
                continue
        product_sku = row[3].strip()
        try:
            product = Product.objects.get(product_sku=product_sku)
        except Exception as e:
            # print("Product not found exception '{}' at row {} with sku {}".format(e, row_id, product_sku))
            # print(row)
            not_found.append(product_sku)
            continue
        else:
            if product.parent_product:
                print("product {} already mapped with parent {} in row {}".format(product.id, product.parent_product.id, row_id))
                continue
            try:
                parent = ParentProduct.objects.get(name=row[0].strip().replace('\\', ''))
            except Exception as e:
                # print("Exception is {}".format(e))
                # print(row[0])
                parent_nf.append(row[0])
                continue
            else:
                product.parent_product = parent
                if product.id in status_data:
                    product.status = status_data[product.id]
                elif str(product.id) in status_data:
                    product.status = status_data[str(product.id)]
                if product.id in mrp_data:
                    product.product_mrp = float(mrp_data[product.id])
                elif str(product.id) in mrp_data:
                    product.product_mrp = float(mrp_data[str(product.id)])
                product.save()
                count += 1
    # print(not_found)
    print(len(not_found))
    # print(parent_nf)
    print(len(parent_nf))
    print(count)
