from django.core.management.base import BaseCommand
from django.core.files import File
import os

from wms.forms import validation_stock_correction
from wms.common_functions import StockMovementCSV
from wms.views import stock_correction_data
from accounts.models import User


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('start', type=int)
        parser.add_argument('nof', type=int)

    def handle(self, *args, **options):
        try:
            start_from_file = options['start']
            nof = options['nof'] + start_from_file
            user = User.objects.get(phone_number='7763886418')
            while start_from_file < nof:
                print("file {}".format(start_from_file))
                f = open('franchise/management/stock_' + str(start_from_file) + '.csv', 'rb')
                data = validation_stock_correction(f, user)
                print("validation done")
                stock_movement_obj = StockMovementCSV.create_stock_movement_csv(user, File(file=f, name='franchise_stock_add'+str(start_from_file)+'.csv'),3)
                print(stock_movement_obj)
                stock_correction = stock_correction_data(data, stock_movement_obj)
                print(stock_correction)
                os.remove('franchise/management/stock_' + str(start_from_file) + '.csv')
                start_from_file += 1

        except Exception as e:
            print(e)



