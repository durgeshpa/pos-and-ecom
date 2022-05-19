import csv

from django.http import HttpResponse


def generate_csv_file_by_data_list_with_filename(data_list, filename):
    # Write error msg in csv sheet.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

    writer = csv.writer(response)
    for row in data_list:
        writer.writerow(row)

    return response
