# Cart Type Choices
from model_utils import Choices


LIST, FUNCTION = 'LIST', 'FUNCTION'

CARD_TYPE_PRODUCT, CARD_TYPE_CAREGORY, CARD_TYPE_BRAND, CARD_TYPE_IMAGE = 'product', 'category', 'brand', 'image'
CARD_TYPE_CHOICES = [
    ('image', 'Image'),
    ('product', 'Product'),
    ('category', 'Category'),
    ('brand', 'Brand'),
    ('text', 'Text')
]

LISTING_SUBTYPE_CHOICE = Choices(
    (1, LIST, 'List'), (2, FUNCTION, 'Function')
)

# Scroll Type Choices
SCROLL_CHOICES = [
    ('noscroll', 'No-Scroll'),
    ('button', 'Button'),
    ('scrollbar', 'Scrollbar')
]

STATUS_CHOICES = (
    ('Active', 'Active'),
    ('Inactive', 'Inactive')
)

PAGE_STATE_CHOICES = (
    ('Draft', 'Draft'),
    ('Staging', 'Staging'),
    ('Published', 'Published')
)

# Landing Page type
PRODUCT, CATEGORY, BRAND = 'PRODUCT', 'CATEGORY', 'BRAND'
LANDING_PAGE = 'LANDING_PAGE'
CATEGORY_B2C = 'CATEGORY_B2C'
LANDING_PAGE_TYPE_CHOICE = Choices(
    (1, PRODUCT, 'Product'), (2, CATEGORY, 'Category'), (3, BRAND, 'Brand')
)

# Function Type Choices
FUNTION_TYPE_CHOICE = Choices(
    (1, PRODUCT, 'Product'), (2, CATEGORY, 'Category'), (3, BRAND, 'Brand')
)

# Image Type Choices
IMAGE_TYPE_CHOICE = Choices(
    (1, PRODUCT, 'Product'), (2, CATEGORY, 'Category'), (3, BRAND, 'Brand'), (4, LANDING_PAGE, 'Landing Page'),
    (5, CATEGORY_B2C, 'B2C Category')
)
