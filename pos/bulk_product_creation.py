import decimal
from copy import deepcopy

from django.db import transaction
from django.apps import apps


def bulk_create_update_validated_products(uploaded_by, shop_id, uploaded_data_by_user_list):
    from pos.common_functions import RetailerProductCls, PosInventoryCls, ProductChangeLogs
    RetailerProduct = apps.get_model('pos.RetailerProduct')
    MeasurementCategory = apps.get_model('pos.MeasurementCategory')
    MeasurementUnit = apps.get_model('pos.MeasurementUnit')

    Product = apps.get_model('products.Product')
    PosInventoryState = apps.get_model('wms.PosInventoryState')
    PosInventoryChange = apps.get_model('wms.PosInventoryChange')

    with transaction.atomic():
        for row in uploaded_data_by_user_list:
            measure_cat_id = None
            if row.get('measurement_category'):
                measure_cat_id = MeasurementCategory.objects.get(category=row.get('measurement_category')).id

            if str(row.get('available_for_online_orders').lower()) == 'yes':
                row['online_enabled'] = True
            else:
                row['online_enabled'] = False

            if row['online_order_price']:
                row['online_price'] = decimal.Decimal(row['online_order_price'])
            else:
                row['online_price'] = None

            if str(row['is_visible']).lower() == 'yes':
                row['is_deleted'] = False
            else:
                row['is_deleted'] = True

            if str(row['product_pack_type']).lower() == 'loose':
                purchase_pack_size = 1
            else:
                purchase_pack_size = int(row.get('purchase_pack_size')) if row.get('purchase_pack_size') else 1

            if row['offer_price']:
                row['offer_price'] = decimal.Decimal(row['offer_price'])
            else:
                row['offer_price'] = None

            if not row['offer_start_date']:
                row['offer_start_date'] = None

            if not row['offer_end_date']:
                row['offer_end_date'] = None

            name, ean, mrp, sp, offer_price, offer_sd, offer_ed, linked_pid, description, stock_qty, \
            online_enabled, online_price, is_visible, product_pack_type, initial_purchase_value = row.get('product_name'), row.get('product_ean_code'), \
                                                       row.get('mrp'), row.get('selling_price'), row.get('offer_price', None), \
                                                       row.get('offer_start_date', None), row.get('offer_end_date', None), None, \
                                                       row.get('description'), row.get('quantity'), row['online_enabled'], \
                                                       row['online_price'], row['is_deleted'], row.get('product_pack_type',None), row.get('initial_purchase_value')

            if row.get('product_id') == '':
                # we need to create this product
                # if else condition for checking whether, Product we are creating is linked with existing product or not
                # with the help of 'linked_product_id'
                measure_cat_id = None
                if row.get('measurement_category'):
                    measure_cat_id = MeasurementCategory.objects.get(category=row.get('measurement_category')).id
                if 'linked_product_sku' in row.keys() and not row.get('linked_product_sku') == '':
                    if row.get('linked_product_sku') != '':
                        # If product is linked with existing product
                        if Product.objects.filter(product_sku=row.get('linked_product_sku')):
                            product = Product.objects.get(product_sku=row.get('linked_product_sku'))
                            r_product = RetailerProductCls.create_retailer_product(shop_id, name, mrp,
                                                                       sp, product.id, 2, description, ean,
                                                                       uploaded_by, 'product',
                                                                       row.get('product_pack_type').lower(),
                                                                       measure_cat_id, None,
                                                                       row.get('status'), offer_price, offer_sd,
                                                                       offer_ed, None, online_enabled, online_price,
                                                                       purchase_pack_size, is_visible,
                                                                                   initial_purchase_value)
                else:
                    # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                    r_product = RetailerProductCls.create_retailer_product(shop_id, name, mrp,
                                                               sp, linked_pid, 1, description, ean, uploaded_by,
                                                               'product', row.get('product_pack_type').lower(),
                                                               measure_cat_id, None, row.get('status'),
                                                               offer_price, offer_sd, offer_ed, None,
                                                               online_enabled, online_price,
                                                               purchase_pack_size, is_visible, initial_purchase_value)
                # Add Inventory
                PosInventoryCls.stock_inventory(r_product.id, PosInventoryState.NEW, PosInventoryState.AVAILABLE,
                                                round(decimal.Decimal(row.get('quantity')), 3), uploaded_by,
                                                r_product.sku,
                                                PosInventoryChange.STOCK_ADD)

            else:
                # we need to update existing product

                if str(row.get('available_for_online_orders').lower()) == 'yes':
                    row['online_enabled'] = True
                else:
                    row['online_enabled'] = False

                if str(row.get('is_visible')).lower() == 'yes':
                    row['is_deleted'] = False
                else:
                    row['is_deleted'] = True

                if row['online_order_price']:
                    row['online_price'] = decimal.Decimal(row['online_order_price'])
                else:
                    row['online_price'] = None

                if row['purchase_pack_size']:
                    if str(row['product_pack_type']).lower() == 'loose':
                        purchase_pack_size = 1
                    else:
                        purchase_pack_size = int(row.get('purchase_pack_size'))
                try:
                    product = RetailerProduct.objects.get(id=row.get('product_id'))
                    old_product = deepcopy(product)

                    if (row.get('linked_product_sku') != '' and Product.objects.get(
                            product_sku=row.get('linked_product_sku'))):
                        linked_product = Product.objects.get(product_sku=row.get('linked_product_sku'))
                        product.linked_product_id = linked_product.id

                    if product.selling_price != row.get('selling_price'):
                        product.selling_price = row.get('selling_price')

                    if product.initial_purchase_value != row.get('initial_purchase_value'):
                        product.initial_purchase_value = row.get('initial_purchase_value')

                    if product.status != row.get('status'):
                        if row.get('status') == 'deactivated':
                            product.status = 'deactivated'
                        else:
                            product.status = "active"

                    if product.is_deleted != row['is_deleted']:
                        product.is_deleted = row['is_deleted']

                    if product.name != row.get('product_name'):
                        product.name = row.get('product_name')

                    if product.online_enabled != row['online_enabled']:
                        product.online_enabled = row['online_enabled']
                    if product.online_price != row['online_price']:
                        product.online_price = row['online_price']

                    if product.description != row.get('description'):
                        product.description = row.get('description')

                    if product.purchase_pack_size != purchase_pack_size:
                        product.purchase_pack_size = purchase_pack_size

                    if row['offer_price']:
                        product.offer_price = decimal.Decimal(row['offer_price'])

                    if row['offer_start_date']:
                        product.offer_start_date = row['offer_start_date']

                    if row['offer_end_date']:
                        product.offer_end_date = row['offer_end_date']

                    if product_pack_type:
                        product.product_pack_type = product_pack_type.lower()

                    product.measurement_category_id = measure_cat_id

                    product.save()

                    # Create discounted products while updating Products
                    if row.get('discounted_price', None):
                        discounted_price = decimal.Decimal(row['discounted_price'])
                        discounted_stock = int(row['discounted_stock'])
                        product_status = 'active' if decimal.Decimal(discounted_stock) > 0 else 'deactivated'

                        initial_state = PosInventoryState.AVAILABLE
                        tr_type = PosInventoryChange.STOCK_UPDATE

                        discounted_product = RetailerProduct.objects.filter(product_ref=product).last()
                        if not discounted_product:

                            initial_state = PosInventoryState.NEW
                            tr_type = PosInventoryChange.STOCK_ADD

                            discounted_product = RetailerProductCls.create_retailer_product(product.shop.id,
                                                                                            product.name,
                                                                                            product.mrp,
                                                                                            discounted_price,
                                                                                            product.linked_product_id,
                                                                                            4,
                                                                                            product.description,
                                                                                            product.product_ean_code,
                                                                                            uploaded_by,
                                                                                            'product',
                                                                                            product.product_pack_type,
                                                                                            product.measurement_category_id,
                                                                                            None, product_status,
                                                                                            None, None, None, product,
                                                                                            False, None)
                        else:
                            RetailerProductCls.update_price(discounted_product.id, discounted_price, product_status,
                                                            uploaded_by, 'product', discounted_product.sku)

                        PosInventoryCls.stock_inventory(discounted_product.id, initial_state,
                                                        PosInventoryState.AVAILABLE, discounted_stock,
                                                        uploaded_by,
                                                        discounted_product.sku, tr_type, None)

                    # Change logs
                    ProductChangeLogs.product_update(product, old_product, uploaded_by, 'product',
                                                     product.sku)
                except:
                    pass
