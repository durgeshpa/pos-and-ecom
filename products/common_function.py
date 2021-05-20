import logging

from rest_framework import status
from rest_framework.response import Response

from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
     ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping
from products.common_validators import get_validate_parent_brand, get_validate_product_hsn
from categories.models import Category

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


class ParentProductCls(object):

    @classmethod
    def create_parent_product(cls, parent_brand, product_hsn,  **validated_data):
        """
            Create Parent Product
        """
        parent_brand = get_validate_parent_brand(parent_brand)
        product_hsn = get_validate_product_hsn(product_hsn)
        return ParentProduct.objects.create(product_hsn=product_hsn['product_hsn'],
                                            parent_brand=parent_brand['parent_brand'], **validated_data)

    @classmethod
    def upload_parent_product_images(cls, parent_product, parent_product_pro_image):
        """
            Delete Existing Images of specific ParentProduct if any & Create Parent Product Images
        """
        if ParentProductImage.objects.filter(parent_product=parent_product).exists():
            ParentProductImage.objects.filter(parent_product=parent_product).delete()

        for image_data in parent_product_pro_image:
            ParentProductImage.objects.create(image=image_data, image_name=image_data.name.rsplit(".", 1)[0],
                                              parent_product=parent_product)

    @classmethod
    def create_parent_product_category(cls, parent_product, parent_product_pro_image):
        """
             Delete Existing Category of specific ParentProduct if any & Create Parent Product Categories
        """
        if ParentProductCategory.objects.filter(parent_product=parent_product).exists():
            ParentProductCategory.objects.filter(parent_product=parent_product).delete()

        for product_category in parent_product_pro_image:
            category = Category.objects.filter(id=product_category['category']).last()
            ParentProductCategory.objects.create(parent_product=parent_product, category=category)

    @classmethod
    def create_parent_product_tax(cls, parent_product, parent_product_pro_tax):
        """
            Delete Existing Tax of specific ParentProduct if any & Create Parent Product Tax
        """
        if ParentProductTaxMapping.objects.filter(parent_product=parent_product).exists():
            ParentProductTaxMapping.objects.filter(parent_product=parent_product).delete()
            
        for tax_data in parent_product_pro_tax:
            tax = Tax.objects.filter(id=tax_data['tax']).last()
            ParentProductTaxMapping.objects.create(parent_product=parent_product, tax=tax)


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True, "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": None}

    return Response(result, status=status_code)


