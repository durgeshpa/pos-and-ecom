import csv
import codecs
import re
import logging

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from products.models import Product
from wms.models import InventoryType
from shops.models import Shop

from wms.common_functions import get_stock
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from .common_function import capping_check, getShopMapping

logger = logging.getLogger(__name__)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


# bulk order validation for csv uploaded
def bulk_order_validation(cart_products_csv, order_type, seller_shop, buyer_shop):
    availableQuantity = []
    error_dict = {}
    reader = csv.reader(codecs.iterdecode(cart_products_csv, 'utf-8', errors='ignore'))
    headers = next(reader, None)
    duplicate_products = []
    qty = 0
    for id, row in enumerate(reader):
        count = 0
        if not row[0]:
            raise ValidationError("Row[" + str(id + 1) + "] | " + headers[0] + ":" + row[0] + " | "
                                  "Product SKU cannot be empty")

        if not row[2] or not re.match("^[\d\,]*$", row[2]):
            raise ValidationError(
                "Row[" + str(id + 1) + "] | " + headers[0] + ":" + row[0] + " | " +
                VALIDATION_ERROR_MESSAGES['EMPTY'] % "qty")

        if order_type == 'DISCOUNTED':
            if not row[3] or not re.match("^[1-9][0-9]{0,}(\.\d{0,2})?$", row[3]):
                raise ValidationError("Row[" + str(id + 1) + "] | " + headers[0] + ":" + row[0] + " | " +
                                      VALIDATION_ERROR_MESSAGES['EMPTY'] % "discounted_price")
        if row[0] in duplicate_products:
            raise ValidationError(_("Row[" + str(id + 1) + "] | " + headers[0] + ":" + row[
                0] + " | Duplicate entries of this product has been uploaded"))
        try:
            product = Product.objects.get(product_sku=row[0])
        except:
            raise ValidationError(
                "Row[" + str(id + 1) + "] | " + headers[0] + ":" + row[0] + " | " + VALIDATION_ERROR_MESSAGES[
                    'INVALID_PRODUCT_SKU'])
        duplicate_products.append(row[0])

        product_price = product.get_current_shop_price(seller_shop, buyer_shop)
        if not product_price:
            raise ValidationError(_("Row[" + str(id + 1) + "] | " + headers[0] + ":" + row[
                0] + " | Product Price Not Available"))

        ordered_qty = int(row[2])
        if row[3] and order_type == 'DISCOUNTED':
            discounted_price = float(row[3])
            per_piece_price = product_price.get_per_piece_price(ordered_qty)
            if per_piece_price < discounted_price:
                raise ValidationError(_("Row[" + str(id + 1) + "] | " + headers[0] + ":" + row[
                    0] + " | Discounted Price can't be more than Product Price."))

        shop = Shop.objects.filter(id=seller_shop.id).last()
        inventory_type = InventoryType.objects.filter(inventory_type='normal').last()

        product_qty_dict = get_stock(shop, inventory_type, [product.id])
        if product_qty_dict.get(product.id) is not None:
            available_quantity = product_qty_dict[product.id]
        else:
            available_quantity = 0
            error_logger.info(f"[retailer_to_sp:BulkOrder]-{row[0]} doesn't exist in warehouse")

        product_available = int(
            int(available_quantity) / int(product.product_inner_case_size))
        availableQuantity.append(product_available)

        # checking capping
        capping = product.get_current_shop_capping(shop, buyer_shop)
        parent_mapping = getShopMapping(buyer_shop)
        if parent_mapping is None:
            message = "Parent Mapping is not Found"
            error_dict[row[0]] = message
        if capping:
            msg = capping_check(capping, parent_mapping, product, ordered_qty, qty)
            if msg[0] is False:
                error_dict[row[0]] = msg[1]

        from audit.views import BlockUnblockProduct
        is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(product, seller_shop)
        if is_blocked_for_audit is True:
            message = "Failed because of SKU {} is Blocked for Audit" \
                .format(str(product.product_sku))
            error_dict[row[0]] = message

        if product_available >= ordered_qty:
            count += 1
        if count == 0:
            message = "Failed because of Ordered quantity is {} > Available quantity {}" \
                .format(str(ordered_qty), str(available_quantity))
            error_dict[row[0]] = message

    return availableQuantity, error_dict
