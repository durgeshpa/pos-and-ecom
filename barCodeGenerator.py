# from reportlab.lib.units import mm
# from reportlab.graphics.barcode import *
# from reportlab.graphics.shapes import Drawing, String
#
# class MyBarcodeDrawing(Drawing):
#     def __init__(self, text_value, *args, **kw):
#         barcode = createBarcodeDrawing('Code128', value=text_value, barHeight=10*mm, humanReadable=True)
#         Drawing.__init__(self,barcode.width,barcode.height,*args,**kw)
#         self.add(barcode, name='barcode')

import os
import shutil
import barcode
from barcode.writer import ImageWriter
import PIL
from PIL import Image
from pyzbar.pyzbar import decode
from io import BytesIO
import base64
import io


def barcodeGen(strVal):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(strVal, writer=ImageWriter())
    fullname = ean.save('strVal')
    with open(fullname, 'rb') as fp:
        ret_str = base64.b64encode(fp.read()).decode('ascii')
    # os.remove(fullname)
    return ret_str


def barcode_gen(value):
    ean = barcode.get_barcode_class('code128')
    ean = ean(value, writer=ImageWriter())
    image = ean.render()
    output_stream = BytesIO()
    image_resize = image.resize((900, 300))
    image_resize.save(output_stream, format='JPEG', quality=150)
    output_stream.seek(0)
    return output_stream


def barcode_decoder(value):
    image = Image.open(value)
    image = image.convert('L')
    data = decode(image)
    return str(data[0][0])




















