import os
import django
from wkhtmltopdf.views import PDFTemplateResponse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
import barcode
from barcode.writer import ImageWriter
import PIL
from PIL import Image
import base64
from fpdf import FPDF
from PIL import Image
import os.path
from os import path


def barcodeGen(strVal):
    image_path = "barcode_tmp/" + strVal + ".png"
    image_path_noext = "barcode_tmp/" + strVal
    if not path.exists(image_path):
        EAN = barcode.get_barcode_class('code128')
        ean = EAN(strVal, writer=ImageWriter())
        fullname = ean.save(image_path_noext)
    with open(image_path, 'rb') as fp:
        ret_str = base64.b64encode(fp.read()).decode('ascii')
    return ret_str


def makePdf(barcode_list):
    template_name = 'admin/wms/barcode.html'
    data = {"barcode_list": barcode_list}

    request = None
    filename = "barcode"
    cmd_option = {"margin-top": 0, "margin-left": 0, "margin-right": 0, "margin-bottom": 0, "zoom": 1,
                  "javascript-delay": 0, "footer-center": "[page]/[topage]", "page-height": 50, "page-width": 75,
                  "no-stop-slow-scripts": True, "quiet": True}
    response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                   context=data, show_content_in_browser=False, cmd_options=cmd_option)

    with open("barcode.pdf", "wb") as f:
        f.write(response.rendered_content)


def merged_barcode_gen(barcode_list):
    for key, value in barcode_list.items():
        barcode = barcodeGen(key)
        barcode_list[key] = {'code': barcode, 'qty': list(range(value))}
    makePdf(barcode_list)


barcode_list = {"B2BZ01SR001-0101": 1, "B2BZ01SR001-0122": 5}
merged_barcode_gen(barcode_list)
