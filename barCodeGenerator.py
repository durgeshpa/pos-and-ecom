
import barcode
import qrcode
from barcode.writer import ImageWriter
import base64
from os import path

from django.http import HttpResponse
from wkhtmltopdf.views import PDFTemplateResponse



def qrCodeGen(file_name, strVal):
    image_path = "qrcode_temp/" + file_name + ".png"
    if not path.exists(image_path):
        img = qrcode.make(strVal)
        fullname = img.save(image_path)
    with open(image_path, 'rb') as fp:
        ret_str = base64.b64encode(fp.read()).decode('ascii')
    return ret_str

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


def makePdf(barcode_list, template_name):
    data = {"barcode_list": barcode_list}

    request = None
    filename = "barcode"
    cmd_option = {"margin-top": 2, "margin-left": 4, "margin-right": 4, "margin-bottom": 0, "zoom": 1,
                  "javascript-delay": 0, "footer-center": "[page]/[topage]", "page-height": 38, "page-width": 76,
                  "no-stop-slow-scripts": True, "quiet": True}
    pdf_data = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                   context=data, show_content_in_browser=False, cmd_options=cmd_option)
    response = HttpResponse(pdf_data.rendered_content, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="barcode.pdf"'
    return response


def merged_barcode_gen(barcode_list, template_name='admin/wms/barcode.html'):
    for key, value in barcode_list.items():
        barcode = barcodeGen(key)
        if value['qty']==0:
            value['qty']=1
        barcode_list[key] = {'code': barcode, 'qty': list(range(value['qty'])), "data": value['data']}
    return makePdf(barcode_list, template_name)
