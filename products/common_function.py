from rest_framework import status
from rest_framework.response import Response

from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
     ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping
from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_product,\
    get_validate_seller_shop
from categories.models import Category


class ParentProductCls(object):

    @classmethod
    def create_parent_product(cls, parent_brand, product_hsn,  **validated_data):
        """
            Create Parent Product
        """
        parent_brand_obj = get_validate_parent_brand(parent_brand)
        product_hsn_obj = get_validate_product_hsn(product_hsn)
        return ParentProduct.objects.create(parent_brand=parent_brand_obj['parent_brand'],
                                            product_hsn=product_hsn_obj['product_hsn'], **validated_data)

    @classmethod
    def update_parent_product(cls, parent_brand, product_hsn, parent_product):
        """
            Update Parent Product
        """
        parent_brand_obj = get_validate_parent_brand(parent_brand)
        product_hsn_obj = get_validate_product_hsn(product_hsn)
        parent_product.parent_brand = parent_brand_obj['parent_brand']
        parent_product.product_hsn = product_hsn_obj['product_hsn']
        parent_product.save()
        return parent_product

    @classmethod
    def upload_parent_product_images(cls, parent_product, parent_product_pro_image):
        """
            Delete Existing Images of specific ParentProduct if any
            Create Parent Product Images
        """
        parent_image = ParentProductImage.objects.filter(parent_product=parent_product)
        if parent_image.exists():
            parent_image.delete()

        for image in parent_product_pro_image:
            ParentProductImage.objects.create(image=image, image_name=image.name.rsplit(".", 1)[0],
                                              parent_product=parent_product)

    @classmethod
    def create_parent_product_category(cls, parent_product, parent_product_pro_category):
        """
             Delete Existing Category of specific ParentProduct if any
             Create Parent Product Categories
        """
        parent_cat = ParentProductCategory.objects.filter(parent_product=parent_product)
        if parent_cat.exists():
            parent_cat.delete()

        for product_category in parent_product_pro_category:
            category = Category.objects.get(id=product_category['category'])
            ParentProductCategory.objects.create(parent_product=parent_product, category=category)

    @classmethod
    def create_parent_product_tax(cls, parent_product, parent_product_pro_tax):
        """
            Delete Existing Tax of specific ParentProduct if any
            Create Parent Product Tax
        """
        parent_tax = ParentProductTaxMapping.objects.filter(parent_product=parent_product)
        if parent_tax.exists():
            parent_tax.delete()

        for tax_data in parent_product_pro_tax:
            tax = Tax.objects.get(id=tax_data['tax'])
            ParentProductTaxMapping.objects.create(parent_product=parent_product, tax=tax)


class ProductCls(object):
    @classmethod
    def create_product_capping(cls, product, seller_shop, **validated_data):
        """
            Create Product Capping
        """
        product_obj = get_validate_product(product)
        seller_shop_obj = get_validate_seller_shop(seller_shop)
        return ProductCapping.objects.create(product=product_obj['product'],
                                             seller_shop=seller_shop_obj['seller_shop'], **validated_data)


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


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]
