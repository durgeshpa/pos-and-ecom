from django.db.models import Q

from products.models import ParentProductImage, ParentProduct, Product, ChildProductImage


def run():
    parent_product_with_no_image = ParentProduct.objects.filter(
        ~Q(id__in=ParentProductImage.objects.all().values_list('parent_product_id', flat=True)))
    for parent in parent_product_with_no_image:
        print("This is Parent-->id[{}], [{}]".format(parent.id, parent))
        child_products = parent.product_parent_product.all()
        # print("Its Child-->{}".format(child_products))
        child_product_with_latest_grn = None
        for child in child_products:
            print("Child of {}-->id[{}], [{}]".format(parent, child.id, child))
            if child.product_pro_image.exists():
                print("Child Image found")
                if child_product_with_latest_grn is None:
                    child_product_with_latest_grn = child
                    continue
                if not child.product_grn_order_product.exists():
                    continue
                if not child_product_with_latest_grn.product_grn_order_product.exists():
                    continue
                if child.product_grn_order_product.latest("created_at").created_at \
                        > child_product_with_latest_grn.product_grn_order_product.latest("created_at").created_at:
                    child_product_with_latest_grn = child
        if child_product_with_latest_grn is not None:
            child_image = child_product_with_latest_grn.product_pro_image.latest("created_at")
            print("Child Image-->{}".format(child_image))
            parent_image = ParentProductImage.objects.create(parent_product=parent, image_name=child_image.image_name, image=child_image.image)
            print("Parent Image created-->{}".format(parent_image))
