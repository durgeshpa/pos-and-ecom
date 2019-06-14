import datetime


def convert_date_format_ddmmmyyyy(scheduled_date):
    #This function converts %d/%m/%Y datetime format to a DD/MMM/YYYY 
    #format and returns a string for the same. 0-06-2019 18:24:21

    #logging.info("converting date format from %d/%m/%Y to %Y-%m-%d")
    return datetime.datetime.strptime(scheduled_date,'%d-%m-%Y %H:%M:%S').strftime("%d/%b/%Y").__str__()
