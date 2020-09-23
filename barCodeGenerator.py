import barcode
from barcode.writer import ImageWriter
import base64
from os import path

from django.http import HttpResponse
from wkhtmltopdf.views import PDFTemplateResponse


def barcodeGen(strVal):
    strVal.isdecimal()
    image_path = "barcode_tmp/" + strVal + ".png"
    image_path_noext = "barcode_tmp/" + strVal
    if not path.exists(image_path):
        if strVal.isdecimal():
            EAN = barcode.get_barcode_class('ean13')
        else:
            EAN = barcode.get_barcode_class('code128')
        ean = EAN(strVal, writer=ImageWriter())
        fullname = ean.save(image_path_noext,{"module_height":9, "font_size": 12, "text_distance": 1, "quiet_zone": 3})
    with open(image_path, 'rb') as fp:
        ret_str = base64.b64encode(fp.read()).decode('ascii')
    return ret_str


def makePdf(barcode_list):
    template_name = 'admin/wms/barcode.html'
    data = {"barcode_list": barcode_list}

    request = None
    filename = "barcode"
    cmd_option = {"margin-top": 2, "margin-left": 0, "margin-right": 0, "margin-bottom": 0, "zoom": 1,
                  "javascript-delay": 0, "footer-center": "[page]/[topage]", "page-height": 50, "page-width": 90,
                  "no-stop-slow-scripts": True, "quiet": True}
    pdf_data = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                   context=data, show_content_in_browser=False, cmd_options=cmd_option)
    response = HttpResponse(pdf_data.rendered_content, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="barcode.pdf"'
    return response

def merged_barcode_gen(barcode_list):
    for key, value in barcode_list.items():
        barcode = barcodeGen(key)
        if value['qty']==0:
            value['qty']=1
        barcode_list[key] = {'code': barcode, 'qty': list(range(value['qty'])), "data": value['data']}
    return makePdf(barcode_list)
