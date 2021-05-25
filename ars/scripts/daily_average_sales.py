import logging

from ars.views import populate_daily_average

def run():
    print('populate_daily_average|Started')
    populate_daily_average()
    print('populate_daily_average|Ended')