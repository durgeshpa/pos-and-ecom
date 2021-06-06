from rest_framework import status
from rest_framework.response import Response

from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
     ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping, ChildProductImage, ProductImage, \
    ProductSourceMapping, DestinationRepackagingCostMapping, ProductPackingMapping
from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_product,\
    get_validate_seller_shop, get_validate_vendor, get_validate_parent_product
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
    def upload_parent_product_images(cls, parent_product,  parent_product_pro_image, product_pro_image):
        """
            Delete Existing Images of specific ParentProduct if any
            Create Parent Product Images
        """
        ids = []
        if parent_product_pro_image:
            for image in parent_product_pro_image:
                ids.append(image['id'])

        parent_image = ParentProductImage.objects.filter(parent_product=parent_product).exclude(
                            id__in=ids).delete()
        if product_pro_image:
            for image in product_pro_image:
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
    def create_child_product(cls, parent_product,  **validated_data):
        """
           Create Child Product
        """
        parent_product_obj = get_validate_parent_product(parent_product)
        return Product.objects.create(parent_product=parent_product_obj['parent_product'], **validated_data)

    @classmethod
    def upload_child_product_images(cls, child_product, product_pro_image):
        """
           Delete Existing Images of specific ParentProduct if any
           Create Parent Product Images
        """
        child_pro_image = ProductImage.objects.filter(product=child_product)
        if child_pro_image.exists():
            child_pro_image.delete()

        for image in product_pro_image:
            ProductImage.objects.create(image=image, image_name=image.name.rsplit(".", 1)[0],
                                        product=child_product)

    @classmethod
    def update_child_product(cls, parent_product, child_product):
        """
            Update Parent Product
        """
        parent_product_obj = get_validate_parent_product(parent_product)
        child_product.parent_product = parent_product_obj['parent_product']
        child_product.save()
        return child_product

    @classmethod
    def create_product_capping(cls, product, seller_shop, **validated_data):
        """
            Create Product Capping
        """
        product_obj = get_validate_product(product)
        seller_shop_obj = get_validate_seller_shop(seller_shop)
        return ProductCapping.objects.create(product=product_obj['product'],
                                             seller_shop=seller_shop_obj['seller_shop'], **validated_data)

    @classmethod
    def create_product_vendor_mapping(cls, product, vendor, **validated_data):
        """
            Create Product Vendor Mapping
        """
        product_obj = get_validate_product(product)
        vendor_obj = get_validate_vendor(vendor)
        return ProductVendorMapping.objects.create(product=product_obj['product'],
                                                   vendor=vendor_obj['vendor'], **validated_data)

    @classmethod
    def update_product_vendor_mapping(cls, product, vendor,  product_vendor_map):
        """
            Update Product Vendor Mapping
        """
        product_obj = get_validate_product(product)
        vendor_obj = get_validate_vendor(vendor)
        product_vendor_map.product = product_obj['product']
        product_vendor_map.vendor = vendor_obj['vendor']
        product_vendor_map.save()
        return product_vendor_map

    @classmethod
    def create_source_product_mapping(cls, child_product, source_sku):
        """
            Create Source Product Mapping
        """
        for source_sku_data in source_sku:
            pro_source_sku = Product.objects.get(id=source_sku_data['source_sku'])
            ProductSourceMapping.objects.create(destination_sku=child_product, source_sku=pro_source_sku)

    @classmethod
    def packing_material_product_mapping(cls, child_product, packing_material_rt):
        """
            Create Packing Material Product Mapping
        """
        for source_sku_data in packing_material_rt:
            pro_packing_sku = Product.objects.get(id=source_sku_data['packing_sku'])
            ProductPackingMapping.objects.create(sku_id=child_product, packing_sku=pro_packing_sku,
                packing_sku_weight_per_unit_sku=source_sku_data['packing_sku_weight_per_unit_sku'])

    @classmethod
    def create_destination_product_mapping(cls, child_product, destination_product_repackaging):
        """
            Create Destination Product Mapping
        """
        for pro_des_data in destination_product_repackaging:
            DestinationRepackagingCostMapping.objects.create(destination=child_product, raw_material=pro_des_data['raw_material'])


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
