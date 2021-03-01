from pos.models import RetailerProduct


class RetailerProductCls(object):

    @classmethod
    def create_retailer_product(cls, shop_id, name, mrp, selling_price, linked_product_id, sku_type, description):
        RetailerProduct.objects.create(shop_id=shop_id, name=name, linked_product_id=linked_product_id,
                                       mrp=mrp, sku_type=sku_type, selling_price=selling_price, description=description)


    @classmethod
    def get_sku_type(cls, sku_type):
        if sku_type == 1:
            return 'CREATED'
        if sku_type == 2:
            return 'LINKED'
        if sku_type == 3:
            return 'LINKED_EDITED'
