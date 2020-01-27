from products.models import Product
import xlrd

def update_hsn_code():
    wb = xlrd.open_workbook('EANCODES.xlsx')
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0,0)
    for i in range(sheet.nrows-1):
        product_ean_code = sheet.cell_value(i+1, 4)
        print(product_ean_code)
        products = Product.objects.filter(id=sheet.cell_value(i+1, 0))
        products.update(product_ean_code=product_ean_code)


if __name__=='__main__':
    update_hsn_code()