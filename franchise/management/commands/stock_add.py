from django.core.management.base import BaseCommand
from django.core.files import File

from wms.forms import validation_stock_correction
from wms.common_functions import StockMovementCSV
from wms.views import stock_correction_data
from accounts.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        f = open('franchise/management/franchise_stock_add.csv', 'rb')
        user = User.objects.get(phone_number='7763886418')
        data = validation_stock_correction(f, user)
        print("validation done")
        stock_movement_obj = StockMovementCSV.create_stock_movement_csv(user, File(file=f, name='franchise_stock_add.csv'), 3)
        print(stock_movement_obj)
        stock_correction = stock_correction_data(data, stock_movement_obj)
        print(stock_correction)

