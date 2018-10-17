from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .forms import ProductCSVForm

def product_csv_upload(request):
    if request.method == 'POST':
        form = ProductCSVForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponse('Form uploaded successfully')
    else:
        form = ProductCSVForm()
    return render(request, 'core/model_form_upload.html', {
        'form': form
    })
