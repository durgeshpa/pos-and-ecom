from import_export import resources
from .models import (Size, Color, Fragrance, Flavor, Weight, PackageSize,
                     Product, ProductPrice, Tax, ParentProduct)


class SizeResource(resources.ModelResource):
    class Meta:
        model = Size
        exclude = ('created_at', 'modified_at')


class ColorResource(resources.ModelResource):
    class Meta:
        model = Color
        exclude = ('created_at', 'modified_at')


class FragranceResource(resources.ModelResource):
    class Meta:
        model = Fragrance
        exclude = ('created_at', 'modified_at')


class FlavorResource(resources.ModelResource):
    class Meta:
        model = Flavor
        exclude = ('created_at', 'modified_at')


class WeightResource(resources.ModelResource):
    class Meta:
        model = Weight
        exclude = ('created_at', 'modified_at')


class PackageSizeResource(resources.ModelResource):
    class Meta:
        model = PackageSize
        exclude = ('created_at', 'modified_at')


class ParentProductResource(resources.ModelResource):
    class Meta:
        model = ParentProduct
        exclude = ('created_at', 'updated_at')


class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        exclude = ('created_at', 'updated_at')


class ProductPriceResource(resources.ModelResource):
    class Meta:
        model = ProductPrice
        exclude = ('created_at', 'modified_at')


class TaxResource(resources.ModelResource):
    class Meta:
        model = Tax
        exclude = ('created_at', 'updated_at')
