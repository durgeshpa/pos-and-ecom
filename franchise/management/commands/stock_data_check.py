from django.core.management.base import BaseCommand
import csv
import codecs
from franchise.views import process_stock_data

class Command(BaseCommand):
    def handle(self, *args, **options):
        f = open('franchise/management/stock_data.csv', 'rb')
        fw = open('franchise/management/stock_data_processed.csv', mode='w')
        reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
        writer = csv.writer(fw)
        process_stock_data(reader, writer)
