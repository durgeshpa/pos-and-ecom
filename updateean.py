from products.models import Product
import xlrd

def update_ean_code():
    wb = xlrd.open_workbook('EANCODES.xlsx')
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0,0)
    for i in range(sheet.nrows-1):
        product_ean_code = str(sheet.cell_value(i+1, 4)).split('.')[0]
        print(product_ean_code)
        products = Product.objects.filter(id=sheet.cell_value(i+1, 0))
        products.update(product_ean_code=product_ean_code)


def update_ean_code_withgfcode():
    wb = xlrd.open_workbook('EANCODE.xlsx')
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0, 0)
    for i in range(sheet.nrows - 1):
        product_ean_code = str(sheet.cell_value(i + 1, 3)).split('.')[0]
        product_gf_code = sheet.cell_value(i + 1, 0)
        print(product_gf_code)
        products = Product.objects.filter(product_gf_code=sheet.cell_value(i + 1, 0))
        print(products)
        products.update(product_ean_code=product_ean_code)

def updateEanCodeMarch():
    wb = xlrd.open_workbook('EANMAPMarch.xlsx')
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0,0)
    for i in range(sheet.nrows-1):
        product_ean_code = str(sheet.cell_value(i+1, 1)).split('.')[0]
        product_gf_code = sheet.cell_value(i+1, 0)
        print(product_gf_code, product_ean_code)
        products = Product.objects.filter(product_gf_code=sheet.cell_value(i+1,0))
        print(products)
        products.update(product_ean_code=product_ean_code)


def updateEanCodeApril():
    wb = xlrd.open_workbook('EAN_Update_2.xlsx')
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0, 0)
    for i in range(sheet.nrows - 1):
        product_ean_code = str(sheet.cell_value(i + 1, 3)).split('.')[0]
        product_gf_code = sheet.cell_value(i + 1, 2)
        print(product_gf_code, product_ean_code)
        products = Product.objects.filter(product_gf_code=sheet.cell_value(i + 1, 2))
        print(products)
        products.update(product_ean_code=product_ean_code)


def update():
    update_ean_code()

def updateean():
    update_ean_code_withgfcode()

def updateEanCode():
    updateEanCodeMarch()