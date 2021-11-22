from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('lpf', type=int)

    def handle(self, *args, **options):
        with open('franchise/management/franchise_stock_add.csv', 'r') as f:
            csvfile = f.readlines()
        linesPerFile = options['lpf']
        filename = 1
        for i in range(0, len(csvfile), linesPerFile):
            with open('franchise/management/stock_' + str(filename) + '.csv', 'w+') as f:
                if filename > 1:
                    f.write(csvfile[0])
                f.writelines(csvfile[i:i + linesPerFile])
            filename += 1