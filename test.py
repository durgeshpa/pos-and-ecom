import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from wkhtmltopdf.views import PDFTemplateResponse

template_name = 'abc.html'
data = None

request = None
filename = "bill"
# cmd_option = {"margin-top": 2, "margin-left": 0, "margin-right": 0, "margin-bottom": 0, "zoom": 1,
#               "javascript-delay": 0, "footer-center": "[page]/[topage]", "page-height": 50, "page-width": 90,
#               "no-stop-slow-scripts": True, "quiet": True}
cmd_option = {"margin-top": 10,"margin-left": 0,"margin-right": 0,"javascript-delay": 0, "footer-center": "[page]/[topage]",
              "page-height": 300, "page-width": 80, "no-stop-slow-scripts": True, "quiet": True, }
pdf_data = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                   context=data, show_content_in_browser=False, cmd_options=cmd_option)
with open("bill.pdf", "wb") as f:
    f.write(pdf_data.rendered_content)

